from uuid import uuid4
from wallet_api.models import Draft, Transaction, now
from sqlalchemy import select
from .amounts import amount_words
from wallet_api.idempotency import canonical, digest


def create_draft(session, user_id, payload):
    payment=payload['payment']
    recent=session.scalar(select(Transaction).where(Transaction.user_id==user_id,
        Transaction.type==payload['kind'], Transaction.payee_ref==str(payment['payee_id'] or payment['bill_id']),
        Transaction.amount_iqd==payment['amount_iqd'], Transaction.status=='succeeded',
        Transaction.created_at>=now()-600).order_by(Transaction.created_at.desc()))
    payload['amount_words']=amount_words(payment['amount_iqd'])
    payload['duplicate_warning']=(f'دفعت نفس المبلغ لنفس الجهة قبل {(now()-recent.created_at)//60} دقايق — متأكد؟' if recent else None)
    draft=Draft(id=str(uuid4()),user_id=user_id,payload_json=canonical(payload),content_hash=digest(payload),
                status='pending',expires_at=now()+120,created_at=now())
    session.add(draft)
    session.flush()
    return draft
