from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_role
from app.models import User
from app.schemas_dashboard import Dashboard, IncomePoint, IncomeSeries

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Every charge belonging to the landlord's own properties.
OWNED_CHARGES = """
    FROM v_charge_balances b
    JOIN leases l ON l.id = b.lease_id
    JOIN units u ON u.id = l.unit_id
    JOIN properties p ON p.id = u.property_id
    WHERE p.owner_id = :owner
"""


def month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def rate(part, whole) -> float:
    return round(float(part) / float(whole) * 100, 1) if whole else 0.0


@router.get("/summary", response_model=Dashboard)
def summary(
    month: str | None = Query(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    as_of: date | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("landlord")),
):
    today = as_of or date.today()
    year, mon = (int(month[:4]), int(month[5:])) if month else (today.year, today.month)
    start, end = month_bounds(year, mon)
    owner = {"owner": user.id}

    occupancy = db.execute(
        text(
            """
            SELECT count(*) AS total_units,
                   count(*) FILTER (WHERE EXISTS (
                       SELECT 1 FROM leases l
                       WHERE l.unit_id = u.id
                         AND l.status = 'active'
                         AND :as_of BETWEEN l.start_date AND l.end_date
                   )) AS occupied_units
            FROM units u
            JOIN properties p ON p.id = u.property_id
            WHERE p.owner_id = :owner
            """
        ),
        {**owner, "as_of": today},
    ).one()

    income = db.execute(
        text(
            f"""
            SELECT COALESCE(SUM(b.amount), 0) AS expected,
                   COALESCE(SUM(b.paid), 0) AS collected
            {OWNED_CHARGES}
              AND b.due_date >= :start AND b.due_date < :end
            """
        ),
        {**owner, "start": start, "end": end},
    ).one()

    overdue = db.execute(
        text(
            f"""
            SELECT COALESCE(SUM(b.outstanding), 0) AS amount, count(*) AS n
            {OWNED_CHARGES}
              AND b.due_date < :as_of AND b.outstanding > 0
            """
        ),
        {**owner, "as_of": today},
    ).one()

    request_rows = db.execute(
        text(
            """
            SELECT m.status, count(*) AS n
            FROM maintenance_requests m
            JOIN units u ON u.id = m.unit_id
            JOIN properties p ON p.id = u.property_id
            WHERE p.owner_id = :owner AND m.status <> 'resolved'
            GROUP BY m.status
            """
        ),
        owner,
    ).all()
    open_requests = {"submitted": 0, "assigned": 0, "in_progress": 0}
    for request_status, n in request_rows:
        open_requests[request_status] = n

    return Dashboard(
        as_of=today,
        month=f"{year}-{mon:02d}",
        total_units=occupancy.total_units,
        occupied_units=occupancy.occupied_units,
        occupancy_rate=rate(occupancy.occupied_units, occupancy.total_units),
        expected_income=income.expected,
        collected_income=income.collected,
        collection_rate=rate(income.collected, income.expected),
        overdue_amount=overdue.amount,
        overdue_charges=overdue.n,
        open_requests=open_requests,
        open_requests_total=sum(open_requests.values()),
    )


@router.get("/income", response_model=IncomeSeries)
def income_by_month(
    year: int | None = Query(None, ge=2000, le=2100),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("landlord")),
):
    year = year or date.today().year
    rows = db.execute(
        text(
            f"""
            SELECT CAST(EXTRACT(MONTH FROM b.due_date) AS integer) AS m,
                   SUM(b.amount) AS expected,
                   SUM(b.paid) AS collected
            {OWNED_CHARGES}
              AND b.due_date >= :start AND b.due_date < :end
            GROUP BY m
            """
        ),
        {"owner": user.id, "start": date(year, 1, 1), "end": date(year + 1, 1, 1)},
    ).all()
    by_month = {r.m: r for r in rows}

    months = []
    for m in range(1, 13):
        r = by_month.get(m)
        months.append(
            IncomePoint(
                month=f"{year}-{m:02d}",
                expected=r.expected if r else Decimal("0"),
                collected=r.collected if r else Decimal("0"),
            )
        )
    return IncomeSeries(year=year, months=months)
