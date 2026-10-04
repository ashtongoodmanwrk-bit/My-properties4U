from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class PropertyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address_line: str = Field(min_length=1, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    postcode: str = Field(min_length=1, max_length=20)


class PropertyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address_line: str | None = Field(default=None, min_length=1, max_length=255)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    postcode: str | None = Field(default=None, min_length=1, max_length=20)


class PropertyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    address_line: str
    city: str
    postcode: str
    created_at: datetime


class UnitCreate(BaseModel):
    unit_number: str = Field(min_length=1, max_length=50)
    bedrooms: int = Field(ge=0, le=20)
    monthly_rent: Decimal = Field(ge=0, max_digits=10, decimal_places=2)


class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    property_id: int
    unit_number: str
    bedrooms: int
    monthly_rent: Decimal
