from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Lease(Base):
    __tablename__ = "leases"
    __table_args__ = (
        CheckConstraint("end_date > start_date", name="ck_leases_dates"),
        CheckConstraint("rent_amount > 0", name="ck_leases_rent_positive"),
        CheckConstraint("due_day BETWEEN 1 AND 28", name="ck_leases_due_day"),
        CheckConstraint(
            "status IN ('active', 'ended', 'cancelled')", name="ck_leases_status"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id"), index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    rent_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    due_day: Mapped[int]
    status: Mapped[str] = mapped_column(String(20), server_default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RentCharge(Base):
    __tablename__ = "rent_charges"
    __table_args__ = (
        UniqueConstraint("lease_id", "due_date", name="uq_rent_charges_lease_due"),
        CheckConstraint("amount > 0", name="ck_rent_charges_amount_positive"),
        CheckConstraint(
            "status IN ('pending', 'partial', 'paid', 'overdue')",
            name="ck_rent_charges_status",
        ),
        Index("ix_rent_charges_due_status", "due_date", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lease_id: Mapped[int] = mapped_column(
        ForeignKey("leases.id", ondelete="CASCADE"), index=True
    )
    due_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(20), server_default="pending")
