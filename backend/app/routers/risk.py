from collections import defaultdict
from datetime import date, timedelta
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_role
from app.models import Property, Unit, User
from app.models_leases import Lease, RentCharge
from app.models_payments import Payment
from app.risk import GRACE_DAYS, PastCharge, band, can_score, features, load_model, probability
from app.schemas_risk import RiskItem, RiskOut

router = APIRouter(prefix="/risk", tags=["risk"])

HORIZON_DAYS = 45
NOTE = (
    "Prototype model trained on synthetic data. Indicative only: "
    "it uses payment history and nothing else."
)


@lru_cache
def get_model() -> dict | None:
    return load_model()


@router.get("", response_model=RiskOut)
def upcoming_risk(
    as_of: date | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("landlord")),
):
    model = get_model()
    if model is None:
        raise HTTPException(status_code=503, detail="Risk model is not available")

    today = as_of or date.today()
    horizon = today + timedelta(days=HORIZON_DAYS)

    paid = (
        select(
            Payment.rent_charge_id.label("charge_id"),
            func.count().label("n"),
            func.max(Payment.paid_at).label("last_paid"),
        )
        .group_by(Payment.rent_charge_id)
        .subquery()
    )
    stmt = (
        select(
            RentCharge.lease_id,
            RentCharge.id,
            RentCharge.due_date,
            RentCharge.amount,
            RentCharge.status,
            Property.name,
            Unit.unit_number,
            User.email,
            func.coalesce(paid.c.n, 0),
            paid.c.last_paid,
        )
        .select_from(RentCharge)
        .join(Lease, Lease.id == RentCharge.lease_id)
        .join(Unit, Unit.id == Lease.unit_id)
        .join(Property, Property.id == Unit.property_id)
        .join(User, User.id == Lease.tenant_id)
        .outerjoin(paid, paid.c.charge_id == RentCharge.id)
        .where(
            Property.owner_id == user.id,
            Lease.status == "active",
            RentCharge.due_date <= horizon,
        )
        .order_by(RentCharge.lease_id, RentCharge.due_date)
    )

    history: dict[int, list[PastCharge]] = defaultdict(list)
    items: list[RiskItem] = []
    for lease_id, charge_id, due, amount, status, prop, unit, email, n, last_paid in db.execute(
        stmt
    ):
        past = history[lease_id]
        if status == "paid" and last_paid is not None:
            past.append(PastCharge((last_paid.date() - due).days, n > 1))
        elif due < today:
            days = (today - due).days
            if days > GRACE_DAYS:  # unpaid and clearly late: counts as a late charge
                past.append(PastCharge(days, n > 0))
        else:
            p = None
            label = "unknown"
            if can_score(past):
                p = probability(model, features(past, float(amount), due.month))
                label = band(p)
            items.append(
                RiskItem(
                    charge_id=charge_id,
                    lease_id=lease_id,
                    property_name=prop,
                    unit_number=unit,
                    tenant_email=email,
                    due_date=due,
                    amount=amount,
                    probability=None if p is None else round(p, 3),
                    band=label,
                )
            )

    items.sort(key=lambda i: (i.probability is None, -(i.probability or 0), i.due_date))
    return RiskOut(items=items[:limit], total=len(items), note=NOTE)
