from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PaymentCreate(BaseModel):
    rent_charge_id: int
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    method: Literal["card", "bank_transfer", "cash"] = "card"


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rent_charge_id: int
    user_id: int
    amount: Decimal
    method: str
    idempotency_key: str
    paid_at: datetime
