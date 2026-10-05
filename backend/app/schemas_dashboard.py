from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class Dashboard(BaseModel):
    as_of: date
    month: str
    total_units: int
    occupied_units: int
    occupancy_rate: float
    expected_income: Decimal
    collected_income: Decimal
    collection_rate: float
    overdue_amount: Decimal
    overdue_charges: int
    open_requests: dict[str, int]
    open_requests_total: int


class IncomePoint(BaseModel):
    month: str
    expected: Decimal
    collected: Decimal


class IncomeSeries(BaseModel):
    year: int
    months: list[IncomePoint]
