import hashlib
import json
from sqlalchemy import select, delete
from .db import immediate
from .models import IdempotencyKey, Transaction, now
from .errors import WalletError


def canonical(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(payload):
    return hashlib.sha256(canonical(payload).encode()).hexdigest()


def cleanup(engine):
    with immediate(engine) as s:
        return s.execute(delete(IdempotencyKey).where(IdempotencyKey.created_at < now() - 86400)).rowcount


def execute_once(engine, payment, kind, key, debit, faults):
    if not key or len(key) > 128:
        raise WalletError('IDEMPOTENCY_REQUIRED')
    fingerprint = digest({'kind': kind, **payment.model_dump()})
    with immediate(engine) as s:
        row = s.scalar(select(IdempotencyKey).where(IdempotencyKey.user_id == payment.user_id, IdempotencyKey.key == key))
        if row:
            if row.request_fingerprint != fingerprint:
                raise WalletError('IDEMPOTENCY_CONFLICT', status=409)
            if row.status == 'done':
                result = json.loads(row.response_json)
                if 'code' in result:
                    raise WalletError(result['code'], result['detail'])
                return result
            if row.locked_until > now():
                raise WalletError('IN_PROGRESS', status=409)
            row.locked_until = now() + 30
        else:
            # Permanent ledger tombstone prevents replay after the 24-hour cache expires.
            tx = s.scalar(select(Transaction).where(Transaction.user_id == payment.user_id, Transaction.idempotency_key == key))
            if tx:
                if tx.request_fingerprint != fingerprint:
                    raise WalletError('IDEMPOTENCY_CONFLICT', status=409)
                return json.loads(tx.receipt_json)
            row = IdempotencyKey(user_id=payment.user_id, key=key, request_fingerprint=fingerprint,
                                 status='in_progress', locked_until=now() + 30)
            s.add(row)
    try:
        with immediate(engine) as s:
            row = s.scalar(select(IdempotencyKey).where(IdempotencyKey.user_id == payment.user_id, IdempotencyKey.key == key))
            # A lease can be reclaimed; re-check the result under the debit lock.
            if row.status == 'done':
                result = json.loads(row.response_json)
            else:
                try:
                    with s.begin_nested():
                        faults.before()
                        result = debit(s, payment, kind, key)
                        tx = s.get(Transaction, result['id'])
                        tx.request_fingerprint = fingerprint
                        tx.receipt_json = canonical(result)
                        faults.before_commit()
                except WalletError as exc:
                    result = {'code': exc.code, 'detail': exc.detail}
                row.status = 'done'
                row.response_json = canonical(result)
        if 'code' in result:
            raise WalletError(result['code'], result['detail'])
        faults.after_commit()
        return result
    except (TimeoutError, RuntimeError):
        with immediate(engine) as s:
            row = s.scalar(select(IdempotencyKey).where(IdempotencyKey.user_id == payment.user_id, IdempotencyKey.key == key))
            if row.status == 'in_progress':
                row.locked_until = 0
        raise
