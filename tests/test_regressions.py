from concurrent.futures import ThreadPoolExecutor
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from wallet_api.models import User,Transaction,Draft
from wallet_api.routes import create_wallet
from agent.wallet_client import WalletClient
from agent.confirm import Confirmer
from test_confirm import flow
from test_wallet import wallet
from test_e2e import web,chat


def test_different_keys_cannot_overdraw(wallet):
    def send(key): return wallet.post('/transfers',json={'user_id':1,'payee_id':1,'amount_iqd':60000},headers={'Idempotency-Key':key}).json()
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(send,['a','b']))
    assert sum(r.get('status')=='succeeded' for r in results)==1
    assert sum(r.get('code')=='INSUFFICIENT_FUNDS' for r in results)==1
    assert wallet.get('/users/1/balance').json()['balance_iqd']==39750


def test_daily_limit(wallet,engine):
    with Session(engine) as s:
        s.get(User,1).daily_limit_iqd=10000;s.commit()
    r=wallet.post('/transfers',json={'user_id':1,'payee_id':1,'amount_iqd':10000},headers={'Idempotency-Key':'limit'})
    assert r.json()['code']=='LIMIT_EXCEEDED'
    assert wallet.get('/users/1/balance').json()['balance_iqd']==100000


def test_unknown_user_and_huge_amount(wallet):
    assert wallet.post('/transfers',json={'user_id':99,'payee_id':1,'amount_iqd':1000},headers={'Idempotency-Key':'bad'}).json()['code']=='UNKNOWN_USER'
    assert wallet.post('/transfers',json={'user_id':1,'payee_id':1,'amount_iqd':10**30},headers={'Idempotency-Key':'bad'}).json()['code']=='AMOUNT_INVALID'


def test_failed_response_can_reconcile(flow,engine):
    d,_=flow; transport=TestClient(create_wallet(engine,True))
    class Lost:
        def post(self,*a,**kw):
            transport.post(*a,**kw);raise httpx.ReadTimeout('lost')
        def get(self,*a,**kw): raise httpx.ReadTimeout('lost')
    c=Confirmer(engine,WalletClient(Lost(),sleep=lambda _:None));r=d.chat(1,'ادفع الوطنية');key=r['card']['draft_id']
    assert c.confirm(1,key,'BILLER_DOWN')['code']=='STATUS_UNKNOWN'
    c.wallet=WalletClient(transport)
    assert c.status(1,key)['code']=='BILLER_UNAVAILABLE'
    with Session(engine) as s: assert s.scalar(select(func.count()).select_from(Transaction).where(Transaction.idempotency_key==key))==0


def test_show_contacts_recovers_unknown(web):
    r=chat(web,'دز 1000 لسامر');cid=r['conversation_id']
    r=chat(web,'عرض الأسماء',cid)
    assert len(r['options'])==24
    r=chat(web,'خالو',cid)
    assert r['card']['payment']['payee_id']==8


def test_inquiry_queue(web):
    r=chat(web,'شكد رصيدي وبعدين دز 1000 لخالو')
    assert r['card']['payment']['payee_id']==8
    assert any('رصيدك' in x for x in r['messages'])


def test_voice_topup_requires_mobile_biller(web):
    r=chat(web,'اشحن الوطنية 10000')
    assert r['code']=='UNKNOWN_BILLER' and 'card' not in r


def test_unreceived_confirm_can_restore_card(web):
    r=chat(web,'دز 1000 لخالو');key=r['card']['draft_id']
    out=web.get('/drafts/'+key+'/status').json()
    assert out['state']=='DRAFT_PENDING' and out['card']['draft_id']==key


def test_confirmed_crash_recovery(flow,engine):
    d,c=flow;r=d.chat(1,'دز 1000 لخالو');key=r['card']['draft_id']
    with Session(engine) as s:
        s.get(Draft,key).status='confirmed';s.get(Draft,key).expires_at=0;s.commit()
    result=c.confirm(1,key)
    assert result['status']=='succeeded'
    assert c.confirm(1,key)['id']==result['id']
