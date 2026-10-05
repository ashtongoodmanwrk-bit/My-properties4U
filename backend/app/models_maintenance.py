from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MaintenanceRequest(Base):
    __tablename__ = "maintenance_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('submitted', 'assigned', 'in_progress', 'resolved')",
            name="ck_maintenance_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'urgent')",
            name="ck_maintenance_priority",
        ),
        CheckConstraint(
            "category IN ('plumbing', 'electrical', 'heating', 'appliance', 'structural', 'other')",
            name="ck_maintenance_category",
        ),
        Index("ix_maintenance_unit_status", "unit_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id"))
    reported_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30))
    priority: Mapped[str] = mapped_column(String(20), server_default="medium")
    status: Mapped[str] = mapped_column(String(20), server_default="submitted")
    assigned_to: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
