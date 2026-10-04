from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int | None
    entity: str
    entity_id: int
    action: str
    old_values: dict | None
    new_values: dict | None
    created_at: datetime
