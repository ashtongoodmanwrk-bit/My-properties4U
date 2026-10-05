from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class LeaseCreate(BaseModel):
    unit_id: int
    tenant_email: EmailStr
    start_date: date
    end_date: date
    rent_amount: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    due_day: int = Field(default=1, ge=1, le=28)

    @model_validator(mode="after")
    def check_dates(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class LeaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_id: int
    tenant_id: int
    start_date: date
    end_date: date
    rent_amount: Decimal
    due_day: int
    status: str
    created_at: datetime


class RentChargeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lease_id: int
    due_date: date
    amount: Decimal
    status: str
