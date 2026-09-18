from sqlalchemy.orm import Session

from app.models import AuditLog


def write_audit(db: Session, action: str, actor_id: int | None = None, entity: str = "", entity_id=None, payload=None):
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
            payload=payload,
        )
    )
