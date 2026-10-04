from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["plumbing", "electrical", "heating", "appliance", "structural", "other"]
Priority = Literal["low", "medium", "high", "urgent"]


class MaintenanceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    category: Category
    priority: Priority = "medium"


class MaintenanceUpdate(BaseModel):
    status: Literal["assigned", "in_progress", "resolved"]
    assigned_to: str | None = Field(default=None, min_length=1, max_length=255)


class MaintenanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_id: int
    reported_by: int
    title: str
    description: str
    category: str
    priority: str
    status: str
    assigned_to: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
