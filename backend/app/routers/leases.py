from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_role
from app.models import Property, Unit, User
from app.models_leases import Lease, RentCharge
from app.schemas_leases import LeaseCreate, LeaseOut, RentChargeOut
from app.schemas_properties import Page

router = APIRouter(prefix="/leases", tags=["leases"])


def generate_due_dates(start: date, end: date, due_day: int) -> list[date]:
    """One due date per month, on due_day, falling within [start, end]."""
    dates = []
    year, month = start.year, start.month
    while True:
        due = date(year, month, due_day)
        if due > end:
            break
        if due >= start:
            dates.append(due)
        month += 1
        if month == 13:
            month = 1
            year += 1
    return dates


def visible_leases(user: User):
    """Base query: landlords see leases on their units, tenants see their own."""
    stmt = select(Lease)
    if user.role == "landlord":
        stmt = (
            stmt.join(Unit, Lease.unit_id == Unit.id)
            .join(Property, Unit.property_id == Property.id)
            .where(Property.owner_id == user.id)
        )
    else:
        stmt = stmt.where(Lease.tenant_id == user.id)
    return stmt


def get_visible_lease(lease_id: int, db: Session, user: User) -> Lease:
    lease = db.scalar(visible_leases(user).where(Lease.id == lease_id))
    if lease is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lease not found")
    return lease


@router.post("", response_model=LeaseOut, status_code=status.HTTP_201_CREATED)
def create_lease(
    data: LeaseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("landlord")),
):
    unit = db.scalar(
        select(Unit)
        .join(Property, Unit.property_id == Property.id)
        .where(Unit.id == data.unit_id, Property.owner_id == user.id)
    )
    if unit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unit not found")

    tenant = db.scalar(
        select(User).where(
            User.email == data.tenant_email.lower(), User.role == "tenant"
        )
    )
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")

    rent = data.rent_amount if data.rent_amount is not None else unit.monthly_rent
    if rent <= 0:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Rent must be greater than zero; set rent_amount or update the unit's rent",
        )

    lease = Lease(
        unit_id=unit.id,
        tenant_id=tenant.id,
        start_date=data.start_date,
        end_date=data.end_date,
        rent_amount=rent,
        due_day=data.due_day,
        status="active",
    )
    db.add(lease)
    try:
        db.flush()  # the exclusion constraint is checked here
    except IntegrityError as exc:
        db.rollback()
        if "ex_leases_no_overlap" in str(exc.orig):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "This unit already has an active lease overlapping those dates",
            )
        raise

    due_dates = generate_due_dates(data.start_date, data.end_date, data.due_day)
    db.add_all(
        RentCharge(lease_id=lease.id, due_date=d, amount=rent) for d in due_dates
    )
    db.commit()  # lease and its rent schedule are saved together or not at all
    db.refresh(lease)
    return lease


@router.get("", response_model=Page[LeaseOut])
def list_leases(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("landlord", "tenant")),
):
    base = visible_leases(user)
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    items = db.scalars(base.order_by(Lease.id).limit(limit).offset(offset)).all()
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/{lease_id}", response_model=LeaseOut)
def get_lease(
    lease_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("landlord", "tenant")),
):
    return get_visible_lease(lease_id, db, user)


@router.get("/{lease_id}/charges", response_model=Page[RentChargeOut])
def list_charges(
    lease_id: int,
    limit: int = Query(24, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("landlord", "tenant")),
):
    lease = get_visible_lease(lease_id, db, user)
    total = db.scalar(
        select(func.count())
        .select_from(RentCharge)
        .where(RentCharge.lease_id == lease.id)
    )
    items = db.scalars(
        select(RentCharge)
        .where(RentCharge.lease_id == lease.id)
        .order_by(RentCharge.due_date)
        .limit(limit)
        .offset(offset)
    ).all()
    return Page(items=items, total=total, limit=limit, offset=offset)
