import json

from sqlalchemy.orm import Session

from app.modules.observability.models import AuditEvent
from app.repositories import utc_now


def record_audit(
    session: Session,
    *,
    actor_type: str,
    actor_id: str,
    action: str,
    resource_type: str = "",
    resource_id: str = "",
    detail: dict | None = None,
    client_ip: str = "",
) -> AuditEvent:
    event = AuditEvent(
        actor_type=actor_type,
        actor_id=actor_id[:64],
        action=action[:80],
        resource_type=resource_type[:48],
        resource_id=str(resource_id)[:64],
        detail_json=json.dumps(detail or {}, ensure_ascii=False, separators=(",", ":")),
        client_ip=client_ip[:64],
        created_at=utc_now(),
    )
    session.add(event)
    return event
