from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import record
from app.database import get_db
from app.deps import require_role
from app.models import Property, Unit, User
from app.models_leases import Lease
from app.models_maintenance import MaintenanceRequest
from app.schemas_maintenance import (
    MaintenanceCreate,
    MaintenanceOut,
    MaintenanceUpdate,
)
from app.schemas_properties import Page

router = APIRouter(prefix="/maintenance", tags=["maintenance"])

# The only legal moves. Anything else is rejected with a 409.
ALLOWED_TRANSITIONS = {
    "submitted": {"assigned"},
    "assigned": {"in_progress"},
    "in_progress": {"resolved"},
    "resolved": set(),
}


def visible_requests(user: User):
    """Landlords see requests on their properties; tenants see their own."""
    stmt = select(MaintenanceRequest)
    if user.role == "landlord":
        stmt = (
            stmt.join(Unit, MaintenanceRequest.unit_id == Unit.id)
            .join(Property, Unit.property_id == Property.id)
            .where(Property.owner_id == user.id)
        )
    else:
        stmt = stmt.where(MaintenanceRequest.reported_by == user.id)
    return stmt


@router.post("", response_model=MaintenanceOut, status_code=status.HTTP_201_CREATED)
def create_request(
    data: MaintenanceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("tenant")),
):
    # The unit comes from the tenant's own lease, never from the request body.
    lease = db.scalar(
        select(Lease)
        .where(Lease.tenant_id == user.id, Lease.status == "active")
        .order_by(Lease.start_date.desc())
        .limit(1)
    )
    if lease is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "You need an active lease to report an issue"
        )

    req = MaintenanceRequest(
        unit_id=lease.unit_id, reported_by=user.id, **data.model_dump()
    )
    db.add(req)
    db.flush()  # assigns req.id
    record(
        db,
        user.id,
        "maintenance_request",
        req.id,
        "create",
        new={
            "unit_id": req.unit_id,
            "title": req.title,
            "category": req.category,
            "priority": req.priority,
        },
    )
    db.commit()
    db.refresh(req)
    return req


@router.get("", response_model=Page[MaintenanceOut])
def list_requests(
    status_filter: Literal["submitted", "assigned", "in_progress", "resolved"]
    | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("landlord", "tenant")),
):
    stmt = visible_requests(user)
    if status_filter:
        stmt = stmt.where(MaintenanceRequest.status == status_filter)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(
        stmt.order_by(MaintenanceRequest.id.desc()).limit(limit).offset(offset)
    ).all()
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/{request_id}", response_model=MaintenanceOut)
def get_request(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("landlord", "tenant")),
):
    req = db.scalar(visible_requests(user).where(MaintenanceRequest.id == request_id))
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    return req


@router.patch("/{request_id}", response_model=MaintenanceOut)
def update_status(
    request_id: int,
    data: MaintenanceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("landlord")),
):
    # Lock the row so two simultaneous updates are handled one after the other.
    req = db.scalar(
        visible_requests(user)
        .where(MaintenanceRequest.id == request_id)
        .with_for_update(of=MaintenanceRequest)
    )
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")

    if data.status not in ALLOWED_TRANSITIONS[req.status]:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot move a request from '{req.status}' to '{data.status}'",
        )

    if data.status == "assigned":
        if not data.assigned_to:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "assigned_to is required when assigning a request",
            )
        req.assigned_to = data.assigned_to

    record(
        db,
        user.id,
        "maintenance_request",
        req.id,
        "status_change",
        old={"status": req.status},
        new={"status": data.status, "assigned_to": req.assigned_to},
    )
    req.status = data.status
    if data.status == "resolved":
        req.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(req)
    return req

