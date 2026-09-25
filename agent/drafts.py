from uuid import uuid4
from wallet_api.models import Draft, now
from wallet_api.idempotency import canonical, digest


def create_draft(session, user_id, payload):
    draft=Draft(id=str(uuid4()),user_id=user_id,payload_json=canonical(payload),content_hash=digest(payload),
                status='pending',expires_at=now()+120,created_at=now())
    session.add(draft)
    session.flush()
    return draft
