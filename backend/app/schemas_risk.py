from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class RiskItem(BaseModel):
    charge_id: int
    lease_id: int
    property_name: str
    unit_number: str
    tenant_email: str
    due_date: date
    amount: Decimal
    probability: float | None
    band: str  # low, medium, high, or unknown when there is too little history


class RiskOut(BaseModel):
    items: list[RiskItem]
    total: int
    note: str
