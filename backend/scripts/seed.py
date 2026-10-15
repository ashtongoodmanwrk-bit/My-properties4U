"""Seed the dev database with demo data.

Run from the backend folder with the venv active:
    python -m scripts.seed --reset
"""

import argparse
import random
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func, select, text

from app.database import SessionLocal
from app.models import Property, Unit, User
from app.models_audit import AuditLog
from app.models_leases import Lease, RentCharge
from app.models_maintenance import MaintenanceRequest
from app.models_payments import Payment
from app.security import hash_password

PASSWORD = "Demo1234!"
METHODS = ["card", "bank_transfer", "cash"]
DUE_DAYS = [1, 1, 5, 15, 1, 10, 1, 20, 5, 1, 15, 25]
# One profile per lease (12 leases): how each tenant's payment history looks.
PROFILES = [
    "good",
    "good",
    "good",
    "late",
    "partial",
    "good",
    "behind",
    "good",
    "late",
    "good",
    "partial",
    "good",
]
LANDLORDS = ["Priya Shah", "Tom Beckett"]
TENANTS = [
    "Alice Moore",
    "Ben Carter",
    "Chloe Evans",
    "Dan Hughes",
    "Emma Clarke",
    "Finn Walker",
    "Grace Turner",
    "Harry Wood",
    "Isla Green",
    "Jack Baker",
    "Kira Patel",
    "Liam Hill",
]
# (landlord index, name, address, city, postcode, bedrooms of each unit)
PROPERTIES = [
    (0, "Harbour View Apartments", "12 Quay Street", "Poole", "BH15 1AB", [1, 1, 2, 2, 2, 3]),
    (0, "Maple Court", "45 Maple Road", "Bournemouth", "BH2 5QT", [1, 2, 2, 3]),
    (1, "Station Road Flats", "8 Station Road", "Southampton", "SO15 2AA", [1, 1, 2, 2]),
    (1, "Oakfield House", "3 Oakfield Lane", "Winchester", "SO23 8DD", [2, 3, 3]),
]
LEASED_PER_PROPERTY = [4, 3, 3, 2]  # 12 leases in total, 5 vacant units

# (lease index, title, description, category, priority, status, assignee, days ago)
REQUESTS = [
    (
        0,
        "Leaking kitchen tap",
        "The cold tap drips constantly.",
        "plumbing",
        "medium",
        "submitted",
        None,
        2,
    ),
    (
        3,
        "No hot water",
        "Boiler shows an error and there is no hot water.",
        "heating",
        "urgent",
        "assigned",
        "Mike's Plumbing",
        4,
    ),
    (
        5,
        "Socket sparks",
        "The living room socket sparks when used.",
        "electrical",
        "high",
        "in_progress",
        "Sparks Electrical",
        6,
    ),
    (
        7,
        "Dishwasher not draining",
        "Water stays in the bottom after a cycle.",
        "appliance",
        "low",
        "resolved",
        "AppliancePro",
        20,
    ),
    (
        2,
        "Damp patch on ceiling",
        "Growing damp patch above the bedroom window.",
        "structural",
        "high",
        "submitted",
        None,
        1,
    ),
    (
        9,
        "Radiator cold",
        "Bedroom radiator never gets warm.",
        "heating",
        "medium",
        "in_progress",
        "Mike's Plumbing",
        9,
    ),
    (
        10,
        "Front door lock stiff",
        "Key is hard to turn.",
        "other",
        "low",
        "resolved",
        "Handy Andy",
        30,
    ),
    (
        4,
        "Bathroom extractor fan noisy",
        "Loud rattling when switched on.",
        "electrical",
        "low",
        "assigned",
        "Sparks Electrical",
        5,
    ),
]


def add_months(d: date, n: int) -> date:
    total = d.year * 12 + (d.month - 1) + n
    return date(total // 12, total % 12 + 1, d.day)


def at_noon(d: date) -> datetime:
    return datetime.combine(d, time(12, 0), tzinfo=UTC)


def log(db, actor_id, entity, entity_id, action, new_values, when, old_values=None):
    db.add(
        AuditLog(
            actor_id=actor_id,
            entity=entity,
            entity_id=entity_id,
            action=action,
            old_values=old_values,
            new_values=new_values,
            created_at=when,
        )
    )


def reset(db) -> None:
    db.execute(
        text(
            "TRUNCATE audit_log, payments, maintenance_requests, rent_charges, "
            "leases, units, properties, users RESTART IDENTITY CASCADE"
        )
    )
    db.commit()
    print("Existing data wiped.")


def make_users(db):
    pw = hash_password(PASSWORD)
    admin = User(email="admin@example.com", password_hash=pw, full_name="Admin User", role="admin")
    landlords = [
        User(email=f"landlord{i}@example.com", password_hash=pw, full_name=n, role="landlord")
        for i, n in enumerate(LANDLORDS, 1)
    ]
    tenants = [
        User(email=f"tenant{i}@example.com", password_hash=pw, full_name=n, role="tenant")
        for i, n in enumerate(TENANTS, 1)
    ]
    db.add_all([admin, *landlords, *tenants])
    db.flush()
    return landlords, tenants


def make_properties(db, rng, landlords):
    """Returns a list of (property, [units])."""
    result = []
    for owner_idx, name, address, city, postcode, bedrooms in PROPERTIES:
        prop = Property(
            owner_id=landlords[owner_idx].id,
            name=name,
            address_line=address,
            city=city,
            postcode=postcode,
        )
        db.add(prop)
        db.flush()
        units = []
        for n, beds in enumerate(bedrooms, 1):
            rent = Decimal(550 + 175 * beds + rng.choice([0, 25, 50]))
            unit = Unit(
                property_id=prop.id,
                unit_number=f"Flat {n}",
                bedrooms=beds,
                monthly_rent=rent,
            )
            db.add(unit)
            units.append(unit)
        db.flush()
        result.append((prop, units))
    return result


def build_charges(lease):
    charges = []
    y, m = lease.start_date.year, lease.start_date.month
    while date(y, m, 1) <= lease.end_date:
        due = date(y, m, lease.due_day)
        if lease.start_date <= due <= lease.end_date:
            charges.append(
                RentCharge(
                    lease_id=lease.id,
                    due_date=due,
                    amount=lease.rent_amount,
                    status="pending",
                )
            )
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return charges


def add_payment(db, rng, charge, tenant, amount, when):
    payment = Payment(
        rent_charge_id=charge.id,
        user_id=tenant.id,
        amount=amount,
        method=rng.choice(METHODS),
        idempotency_key=f"seed-{charge.id}-1",
        paid_at=when,
    )
    db.add(payment)
    db.flush()
    log(
        db,
        tenant.id,
        "payment",
        payment.id,
        "create",
        {"rent_charge_id": charge.id, "amount": str(amount), "method": payment.method},
        when,
    )


def make_leases_and_payments(db, rng, props, tenants, today):
    leased = []  # (lease, tenant, landlord_id)
    first_of_month = today.replace(day=1)
    i = 0
    for (prop, units), count in zip(props, LEASED_PER_PROPERTY, strict=True):
        for unit in units[:count]:
            tenant = tenants[i]
            start = add_months(first_of_month, -(3 + i % 4))
            end = add_months(start, 12) - timedelta(days=1)
            lease = Lease(
                unit_id=unit.id,
                tenant_id=tenant.id,
                start_date=start,
                end_date=end,
                rent_amount=unit.monthly_rent,
                due_day=DUE_DAYS[i],
                status="active",
            )
            db.add(lease)
            db.flush()
            log(
                db,
                prop.owner_id,
                "lease",
                lease.id,
                "create",
                {
                    "unit_id": unit.id,
                    "tenant_id": tenant.id,
                    "start_date": str(start),
                    "end_date": str(end),
                    "rent_amount": str(lease.rent_amount),
                },
                at_noon(start - timedelta(days=7)),
            )

            charges = build_charges(lease)
            db.add_all(charges)
            db.flush()
            past = [c for c in charges if c.due_date < today]
            future = [c for c in charges if c.due_date >= today]

            profile = PROFILES[i]
            if profile == "partial":
                fully_paid, unpaid, half = past[:-1], [], past[-1:]
            else:
                n = {"late": 1, "behind": 2}.get(profile, 0)
                fully_paid, unpaid, half = past[: len(past) - n], past[len(past) - n :], []

            for c in fully_paid:
                when = at_noon(c.due_date - timedelta(days=rng.randint(0, 2)))
                add_payment(db, rng, c, tenant, c.amount, when)
                c.status = "paid"
            for c in unpaid:
                c.status = "overdue"
            for c in half:
                part = (c.amount * Decimal("0.5")).quantize(Decimal("0.01"))
                add_payment(db, rng, c, tenant, part, at_noon(c.due_date))
                c.status = "overdue"  # partial payment on an overdue charge stays overdue
            if profile == "partial" and future:
                c = future[0]
                part = (c.amount * Decimal("0.3")).quantize(Decimal("0.01"))
                add_payment(db, rng, c, tenant, part, datetime.now(UTC))
                c.status = "partial"

            leased.append((lease, tenant, prop.owner_id))
            i += 1
    db.flush()
    return leased


def make_maintenance(db, leased):
    now = datetime.now(UTC)
    for idx, title, desc, category, priority, status, assignee, days_ago in REQUESTS:
        lease, tenant, landlord_id = leased[idx]
        created = now - timedelta(days=days_ago)
        updated = created if status == "submitted" else created + timedelta(days=1)
        resolved = updated + timedelta(days=1) if status == "resolved" else None
        req = MaintenanceRequest(
            unit_id=lease.unit_id,
            reported_by=tenant.id,
            title=title,
            description=desc,
            category=category,
            priority=priority,
            status=status,
            assigned_to=assignee,
            created_at=created,
            updated_at=updated,
            resolved_at=resolved,
        )
        db.add(req)
        db.flush()
        log(
            db,
            tenant.id,
            "maintenance_request",
            req.id,
            "create",
            {"title": title, "status": "submitted"},
            created,
        )
        if status != "submitted":
            log(
                db,
                landlord_id,
                "maintenance_request",
                req.id,
                "status_change",
                {"status": status, "assigned_to": assignee},
                updated,
                old_values={"status": "submitted"},
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="wipe all data first")
    args = parser.parse_args()

    rng = random.Random(42)  # same data every run
    today = date.today()

    with SessionLocal() as db:
        if args.reset:
            reset(db)
        elif db.scalar(select(func.count()).select_from(User)):
            print("Database already has users. Re-run with --reset to wipe and re-seed.")
            return

        landlords, tenants = make_users(db)
        props = make_properties(db, rng, landlords)
        leased = make_leases_and_payments(db, rng, props, tenants, today)
        make_maintenance(db, leased)
        db.commit()

        counts = {
            "users": db.scalar(select(func.count()).select_from(User)),
            "properties": db.scalar(select(func.count()).select_from(Property)),
            "units": db.scalar(select(func.count()).select_from(Unit)),
            "leases": db.scalar(select(func.count()).select_from(Lease)),
            "rent charges": db.scalar(select(func.count()).select_from(RentCharge)),
            "payments": db.scalar(select(func.count()).select_from(Payment)),
            "maintenance": db.scalar(select(func.count()).select_from(MaintenanceRequest)),
            "audit entries": db.scalar(select(func.count()).select_from(AuditLog)),
        }
        for name, n in counts.items():
            print(f"{name}: {n}")
        print(f"Done. Log in with any demo email and password {PASSWORD}")


if __name__ == "__main__":
    main()
