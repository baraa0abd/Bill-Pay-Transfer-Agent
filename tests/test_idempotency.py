from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from wallet_api.models import Transaction, IdempotencyKey
from wallet_api.routes import create_wallet
from wallet_api.idempotency import cleanup
from agent.wallet_client import WalletClient
from test_wallet import wallet

BODY = {'user_id': 1, 'payee_id': 1, 'amount_iqd': 1000}


def test_fifty_concurrent(wallet, engine):
    def send(_):
        return wallet.post('/transfers', json=BODY, headers={'Idempotency-Key':'same'})
    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(send, range(50)))
    assert all(r.status_code in [200, 409] for r in results)
    assert len({r.json()['id'] for r in results if r.status_code == 200}) == 1
    assert wallet.get('/users/1/balance').json()['balance_iqd'] == 98750
    assert len(wallet.get('/users/1/transactions').json()) == 1


def test_conflict(wallet):
    assert wallet.post('/transfers', json=BODY, headers={'Idempotency-Key':'same'}).status_code == 200
    assert wallet.post('/transfers', json={**BODY, 'amount_iqd':2000}, headers={'Idempotency-Key':'same'}).json()['code'] == 'IDEMPOTENCY_CONFLICT'


def test_missing_key(wallet):
    assert wallet.post('/transfers', json=BODY).status_code == 400


def test_cleanup_tombstone(wallet, engine):
    first = wallet.post('/transfers', json=BODY, headers={'Idempotency-Key':'same'}).json()
    with Session(engine) as s:
        row = s.scalar(select(IdempotencyKey))
        row.created_at = 0
        s.commit()
    assert cleanup(engine) == 1
    second = wallet.post('/transfers', json=BODY, headers={'Idempotency-Key':'same'}).json()
    assert first == second


def test_expired_lease(wallet, engine):
    from wallet_api.idempotency import digest
    from wallet_api.schemas import Payment
    with Session(engine) as s:
        s.add(IdempotencyKey(user_id=1, key='lease', request_fingerprint=digest({'kind':'transfer', **Payment(**BODY).model_dump()}), status='in_progress', locked_until=0))
        s.commit()
    assert wallet.post('/transfers', json=BODY, headers={'Idempotency-Key':'lease'}).status_code == 200
