from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import record
from app.database import get_db
from app.deps import require_role
from app.models import Property, Unit, User
from app.models_leases import Lease, RentCharge
from app.models_payments import Payment
from app.schemas_payments import PaymentCreate, PaymentOut
from app.schemas_properties import Page

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(
    data: PaymentCreate,
    response: Response,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("tenant")),
):
    # 1. Lock the charge row. Any other payment for this charge waits here
    #    until this transaction commits or rolls back.
    charge = db.scalar(
        select(RentCharge)
        .join(Lease, RentCharge.lease_id == Lease.id)
        .where(RentCharge.id == data.rent_charge_id, Lease.tenant_id == user.id)
        .with_for_update(of=RentCharge)
    )
    if charge is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rent charge not found")

    # 2. Idempotency: checked while holding the lock, so a concurrent retry
    #    with the same key sees the first request's committed payment.
    existing = db.scalar(
        select(Payment).where(
            Payment.user_id == user.id, Payment.idempotency_key == idempotency_key
        )
    )
    if existing is not None:
        if existing.rent_charge_id != charge.id or existing.amount != data.amount:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Idempotency key was already used for a different payment",
            )
        response.status_code = status.HTTP_200_OK  # replay: same result, no new charge
        return existing

    # 3. Balance check (reads committed payments, after the lock is held).
    paid = Decimal(
        db.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.rent_charge_id == charge.id
            )
        )
    )
    remaining = charge.amount - paid
    if remaining <= 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "This charge is already paid")
    if data.amount > remaining:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Payment exceeds the remaining balance of {remaining}",
        )

    # 4. Record the payment and update the charge in the same transaction.
    payment = Payment(
        rent_charge_id=charge.id,
        user_id=user.id,
        amount=data.amount,
        method=data.method,
        idempotency_key=idempotency_key,
    )
    db.add(payment)
    if data.amount == remaining:
        charge.status = "paid"
    elif charge.status != "overdue":
        charge.status = "partial"
    try:
        db.flush()  # assigns payment.id
        record(
            db,
            user.id,
            "payment",
            payment.id,
            "create",
            new={
                "rent_charge_id": charge.id,
                "amount": data.amount,
                "method": data.method,
                "charge_status": charge.status,
            },
        )
        db.commit()
    except IntegrityError:
        # Backstop: the unique constraint caught a duplicate key we missed.
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Duplicate payment request")
    db.refresh(payment)
    return payment


@router.get("", response_model=Page[PaymentOut])
def list_payments(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("landlord", "tenant")),
):
    stmt = select(Payment)
    if user.role == "landlord":
        stmt = (
            stmt.join(RentCharge, Payment.rent_charge_id == RentCharge.id)
            .join(Lease, RentCharge.lease_id == Lease.id)
            .join(Unit, Lease.unit_id == Unit.id)
            .join(Property, Unit.property_id == Property.id)
            .where(Property.owner_id == user.id)
        )
    else:
        stmt = stmt.where(Payment.user_id == user.id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(Payment.id.desc()).limit(limit).offset(offset)).all()
    return Page(items=items, total=total, limit=limit, offset=offset)
