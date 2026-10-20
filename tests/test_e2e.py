import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app import create_app
from data.seed import load_seed
from wallet_api.models import Transaction,Draft,User

@pytest.fixture
def web(engine):
    load_seed(engine)
    return TestClient(create_app(engine,demo_mode=True),headers={'X-User-ID':'1'})


def chat(web,text,cid=None): return web.post('/chat',json={'user_id':1,'conversation_id':cid,'text':text}).json()
def confirm(web,r,headers=None): return web.post('/confirm',json={'draft_id':r['card']['draft_id']},headers=headers or {}).json()

@pytest.mark.parametrize('flow',['transfer','bill','ahmed','electricity','unknown','insufficient','two','cancel','double','fault'])
def test_http_flows(web,engine,flow):
    with Session(engine) as s: before=s.scalar(select(func.count()).select_from(Transaction))
    expected=0
    if flow in ['transfer','double','fault']:
        r=chat(web,'دز 10000 لخالو'); key=r['card']['draft_id']
        out=confirm(web,r,{'X-Fault':'DROP_RESPONSE_AFTER_COMMIT'} if flow=='fault' else None)
        assert out['result']['status']=='succeeded';expected=1
        if flow=='double': assert confirm(web,r)['result']['id']==out['result']['id']
    elif flow=='bill':
        r=chat(web,'ادفع الوطنية'); assert confirm(web,r)['result']['status']=='succeeded';expected=1
    elif flow=='ahmed':
        r=chat(web,'دز 50000 لأحمد'); assert len(r['options'])==3
        r=chat(web,'2',r['conversation_id']);assert r['card']['payment']['payee_id']==2
    elif flow=='electricity':
        r=chat(web,'ادفع الكهرباء'); assert len(r['options'])==2
        r=chat(web,'2',r['conversation_id']);assert r['card']['display']['biller_id']==2
    elif flow=='unknown': assert chat(web,'دز 50000 لسامر')['code']=='UNKNOWN_PAYEE'
    elif flow=='insufficient': assert chat(web,'دز نص مليون لخالو')['code']=='INSUFFICIENT_FUNDS'
    elif flow=='two':
        r=chat(web,'دز 10000 لخالو وبعدين ادفع الوطنية');r=confirm(web,r)
        assert r['card']['kind']=='bill_payment';assert confirm(web,r)['result']['status']=='succeeded';expected=2
    elif flow=='cancel':
        r=chat(web,'دز 10000 لخالو'); assert web.post('/cancel',json={'draft_id':r['card']['draft_id']}).json()['result']['code']=='CANCELLED'
        assert confirm(web,r)['result']['code']=='DRAFT_CANCELLED'
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(Transaction))-before==expected
        if flow in ['unknown','insufficient']: assert s.scalar(select(func.count()).select_from(Draft).where(Draft.status=='pending'))==0


def test_mock_identity(web):
    r=chat(web,'دز 10000 لخالو')
    assert web.post('/confirm',json={'draft_id':r['card']['draft_id']},headers={'X-User-ID':'2'}).json()['result']['code']=='DRAFT_FORBIDDEN'
    assert web.post('/chat',json={'user_id':2,'text':'مرحبا'}).status_code==403


def test_page_and_reload(web):
    page=web.get('/').text
    assert 'confirm-card' in page and 'dir="rtl"' in page and 'textContent' in page
    r=chat(web,'دز 10000 لخالو')
    recovered=web.get('/conversations/'+r['conversation_id']).json()
    assert recovered['card']['draft_id']==r['card']['draft_id']


def test_account_names_who_was_paid(web):
    r=chat(web,'دز 10000 لخالو'); confirm(web,r)
    latest=web.get('/account').json()['transactions'][0]
    assert latest['name'] and latest['type']=='transfer' and latest['amount_iqd']==10000
