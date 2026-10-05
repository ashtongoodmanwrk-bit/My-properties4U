from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_role
from app.models import Property, Unit, User
from app.schemas_properties import (
    Page,
    PropertyCreate,
    PropertyOut,
    PropertyUpdate,
    UnitCreate,
    UnitOut,
)

router = APIRouter(prefix="/properties", tags=["properties"])


def get_owned_property(property_id: int, db: Session, user: User) -> Property:
    prop = db.scalar(
        select(Property).where(Property.id == property_id, Property.owner_id == user.id)
    )
    if prop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Property not found")
    return prop


@router.post("", response_model=PropertyOut, status_code=status.HTTP_201_CREATED)
def create_property(
    data: PropertyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("landlord")),
):
    prop = Property(owner_id=user.id, **data.model_dump())
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


@router.get("", response_model=Page[PropertyOut])
def list_properties(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("landlord")),
):
    total = db.scalar(
        select(func.count()).select_from(Property).where(Property.owner_id == user.id)
    )
    items = db.scalars(
        select(Property)
        .where(Property.owner_id == user.id)
        .order_by(Property.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/{property_id}", response_model=PropertyOut)
def get_property(
    property_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("landlord")),
):
    return get_owned_property(property_id, db, user)


@router.patch("/{property_id}", response_model=PropertyOut)
def update_property(
    property_id: int,
    data: PropertyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("landlord")),
):
    prop = get_owned_property(property_id, db, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(prop, field, value)
    db.commit()
    db.refresh(prop)
    return prop


@router.post(
    "/{property_id}/units",
    response_model=UnitOut,
    status_code=status.HTTP_201_CREATED,
)
def create_unit(
    property_id: int,
    data: UnitCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("landlord")),
):
    prop = get_owned_property(property_id, db, user)
    unit = Unit(property_id=prop.id, **data.model_dump())
    db.add(unit)
    try:
        db.commit()
    except IntegrityError:
        # The unique (property_id, unit_number) constraint enforces this.
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Unit number already exists in this property")
    db.refresh(unit)
    return unit


@router.get("/{property_id}/units", response_model=Page[UnitOut])
def list_units(
    property_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("landlord")),
):
    prop = get_owned_property(property_id, db, user)
    total = db.scalar(select(func.count()).select_from(Unit).where(Unit.property_id == prop.id))
    items = db.scalars(
        select(Unit)
        .where(Unit.property_id == prop.id)
        .order_by(Unit.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return Page(items=items, total=total, limit=limit, offset=offset)
