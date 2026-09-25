import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from wallet_api.models import User, Contact, Biller, UserBiller, Bill
from wallet_api.routes import create_wallet


@pytest.fixture
def wallet(engine):
    with Session(engine) as s:
        s.add(User(id=1, name='علي', phone='07000000000', balance_iqd=100000, daily_limit_iqd=200000))
        s.add(Biller(id=1, name_ar='الكهرباء', category='electricity_national', provider='grid'))
        s.commit()
        s.add(Contact(id=1, user_id=1, display_name='أحمد', normalized_name='احمد', phone='07000004567'))
        s.add(UserBiller(id=1, user_id=1, biller_id=1, account_number='123', label='البيت'))
        s.commit()
        s.add(Bill(id=1, user_biller_id=1, period='2026-09', amount_iqd=10000, due_date='2026-10-01', status='unpaid'))
        s.commit()
    return TestClient(create_wallet(engine))


def test_transfer(wallet):
    r = wallet.post('/transfers', json={'user_id': 1, 'payee_id': 1, 'amount_iqd': 50000}, headers={'Idempotency-Key':'one'})
    assert r.status_code == 200
    assert r.json()['balance_iqd'] == 49750


def test_insufficient(wallet):
    r = wallet.post('/transfers', json={'user_id': 1, 'payee_id': 1, 'amount_iqd': 150000}, headers={'Idempotency-Key':'one'})
    assert r.json()['code'] == 'INSUFFICIENT_FUNDS'
    assert wallet.get('/users/1/balance').json()['balance_iqd'] == 100000


def test_paid(wallet):
    body = {'user_id': 1, 'bill_id': 1, 'amount_iqd': 10000}
    assert wallet.post('/bill-payments', json=body, headers={'Idempotency-Key':'one'}).status_code == 200
    assert wallet.post('/bill-payments', json=body, headers={'Idempotency-Key':'two'}).json()['code'] == 'BILL_ALREADY_PAID'


@pytest.mark.parametrize('amount', [0, -1, 1.2, '5000', True])
def test_invalid(wallet, amount):
    r = wallet.post('/transfers', json={'user_id': 1, 'payee_id': 1, 'amount_iqd': amount}, headers={'Idempotency-Key':'one'})
    assert r.json()['code'] == 'AMOUNT_INVALID'
