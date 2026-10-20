import csv
import io
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_role
from app.models import Property, Unit, User
from app.models_leases import Lease, RentCharge
from app.models_payments import Payment

router = APIRouter(prefix="/statements", tags=["statements"])

HEADER = ["Property", "Unit", "Tenant", "Due date", "Amount", "Paid", "Outstanding", "Status"]

# Spreadsheets run cells that start with these characters as formulas.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value: str) -> str:
    """Stop text typed by users from being run as a formula (CSV injection)."""
    if value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


@router.get("")
def monthly_statement(
    month: str = Query(..., pattern=r"^(19|20)\d{2}-(0[1-9]|1[0-2])$", description="YYYY-MM"),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("landlord", "tenant")),
):
    year, mon = int(month[:4]), int(month[5:])
    start = date(year, mon, 1)
    end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)

    paid = (
        select(Payment.rent_charge_id.label("charge_id"), func.sum(Payment.amount).label("paid"))
        .group_by(Payment.rent_charge_id)
        .subquery()
    )
    stmt = (
        select(
            Property.name,
            Unit.unit_number,
            User.email,
            RentCharge.due_date,
            RentCharge.amount,
            func.coalesce(paid.c.paid, 0).label("paid"),
            RentCharge.status,
        )
        .select_from(RentCharge)
        .join(Lease, Lease.id == RentCharge.lease_id)
        .join(Unit, Unit.id == Lease.unit_id)
        .join(Property, Property.id == Unit.property_id)
        .join(User, User.id == Lease.tenant_id)
        .outerjoin(paid, paid.c.charge_id == RentCharge.id)
        .where(RentCharge.due_date >= start, RentCharge.due_date < end)
        .order_by(RentCharge.due_date, Property.name, Unit.unit_number)
    )
    # Tenants only ever see their own charges, landlords only their own properties'.
    if user.role == "tenant":
        stmt = stmt.where(Lease.tenant_id == user.id)
    else:
        stmt = stmt.where(Property.owner_id == user.id)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(HEADER)
    for name, unit_number, email, due_date, amount, paid_total, status in db.execute(stmt):
        outstanding = max(Decimal(amount) - Decimal(paid_total), Decimal("0"))
        writer.writerow(
            [
                safe_cell(name),
                safe_cell(unit_number),
                safe_cell(email),
                due_date.isoformat(),
                f"{Decimal(amount):.2f}",
                f"{Decimal(paid_total):.2f}",
                f"{outstanding:.2f}",
                status,
            ]
        )

    return Response(
        content=buffer.getvalue().encode("utf-8-sig"),  # the BOM makes Excel read it as UTF-8
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="statement-{month}.csv"'},
    )
