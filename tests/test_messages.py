import pytest
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from agent.messages_ar import message, MESSAGES
from agent.wallet_client import WalletClient
from agent.confirm import Confirmer
from wallet_api.routes import create_wallet
from wallet_api.models import Transaction
from test_confirm import flow

@pytest.mark.parametrize('code',list(MESSAGES))
def test_error_messages(code):
    text=message({'code':code})
    assert text and 'تم الدفع' not in text

@pytest.mark.parametrize('fault,success',[('DROP_RESPONSE_AFTER_COMMIT',True),('CRASH_BEFORE_COMMIT',True),('DELAY_MS=1',True),('BILLER_DOWN',False)])
def test_message_matches_ledger(flow,engine,fault,success):
    d,c=flow; r=d.chat(1,'ادفع الوطنية'); key=r['card']['draft_id']
    result=c.confirm(1,key,fault)
    with Session(engine) as s:
        tx=s.scalar(select(Transaction).where(Transaction.idempotency_key==key))
        assert bool(tx)==success
        assert ('تم الدفع' in message(result))==bool(tx)


def test_unknown_then_reconciled(flow,engine):
    d,_=flow; transport=TestClient(create_wallet(engine,True))
    class LostTransport:
        def post(self,*args,**kwargs):
            transport.post(*args,**kwargs)
            raise httpx.ReadTimeout('lost')
        def get(self,*args,**kwargs):
            raise httpx.ReadTimeout('unavailable')
    c=Confirmer(engine,WalletClient(LostTransport(),sleep=lambda _:None))
    r=d.chat(1,'دز 1000 لخالو'); key=r['card']['draft_id']
    result=c.confirm(1,key)
    assert result['code']=='STATUS_UNKNOWN'
    assert 'ما انخصم' not in message(result) and 'تم الدفع' not in message(result)
    c.wallet=WalletClient(transport)
    resolved=c.status(1,key)
    assert resolved['status']=='succeeded' and 'تم الدفع' in message(resolved)
    with Session(engine) as s:
        assert len(list(s.scalars(select(Transaction).where(Transaction.idempotency_key==key))))==1
