import pytest
from fastapi.testclient import TestClient
from wallet_api.routes import create_wallet
from agent.wallet_client import WalletClient
from test_wallet import wallet


@pytest.mark.parametrize('fault', ['DROP_RESPONSE_AFTER_COMMIT', 'CRASH_BEFORE_COMMIT', 'DELAY_MS=1'])
def test_retry(wallet, engine, fault):
    transport = TestClient(create_wallet(engine, demo_mode=True))
    client = WalletClient(transport, sleep=lambda _:None)
    body = {'user_id':1, 'payee_id':1, 'amount_iqd':1000}
    result = client.execute('transfer', body, 'key', fault)
    assert result['status'] == 'succeeded'
    assert client.execute('transfer', body, 'key')['id'] == result['id']
    assert len(wallet.get('/users/1/transactions').json()) == 1
    assert wallet.get('/users/1/balance').json()['balance_iqd'] == 98750


def test_biller_down(wallet, engine):
    client = WalletClient(TestClient(create_wallet(engine, demo_mode=True)), sleep=lambda _:None)
    result = client.execute('bill_payment', {'user_id':1,'bill_id':1,'amount_iqd':10000}, 'down', 'BILLER_DOWN')
    assert result['code'] == 'BILLER_UNAVAILABLE'
    assert wallet.get('/users/1/balance').json()['balance_iqd'] == 100000
