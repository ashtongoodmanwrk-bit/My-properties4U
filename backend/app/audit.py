import json

from sqlalchemy.orm import Session

from app.models_audit import AuditLog


def _jsonable(values):
    if values is None:
        return None
    # default=str turns Decimals and dates into strings
    return json.loads(json.dumps(values, default=str))


def record(
    db: Session,
    actor_id: int | None,
    entity: str,
    entity_id: int,
    action: str,
    old: dict | None = None,
    new: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            entity=entity,
            entity_id=entity_id,
            action=action,
            old_values=_jsonable(old),
            new_values=_jsonable(new),
        )
    )
