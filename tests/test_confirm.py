import ast
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from agent.confirm import Confirmer
from agent.dialogue import Dialogue
from agent.wallet_client import WalletClient
from wallet_api.models import Draft,Transaction,now
from wallet_api.routes import create_wallet
from data.seed import load_seed

@pytest.fixture
def flow(engine):
    load_seed(engine)
    confirmer=Confirmer(engine,WalletClient(TestClient(create_wallet(engine,True)),sleep=lambda _:None))
    return Dialogue(engine,confirmer=confirmer),confirmer


def test_double_tap(flow,engine):
    d,c=flow; r=d.chat(1,'دز 50000 لخالو'); key=r['card']['draft_id']
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:c.confirm(1,key),range(2)))
    assert results[0]['id']==results[1]['id']
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(Transaction).where(Transaction.idempotency_key==key))==1

@pytest.mark.parametrize('change,code',[('expired','DRAFT_EXPIRED'),('tampered','DRAFT_TAMPERED'),('superseded','DRAFT_SUPERSEDED'),('owner','DRAFT_FORBIDDEN')])
def test_invalid_draft(flow,engine,change,code):
    d,c=flow; r=d.chat(1,'دز 50000 لخالو'); key=r['card']['draft_id']
    with Session(engine) as s:
        draft=s.get(Draft,key)
        if change=='expired': draft.expires_at=now()-1
        if change=='tampered': draft.payload_json=draft.payload_json.replace('50000','10000')
        if change=='superseded': draft.status='superseded'
        s.commit()
    assert c.confirm(2 if change=='owner' else 1,key)['code']==code
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(Transaction).where(Transaction.idempotency_key==key))==0

@pytest.mark.parametrize('text',['اوك','يمكن','زين','نعم','أكد الآن','لا تأكد'])
def test_vague(flow,engine,text):
    d,c=flow; r=d.chat(1,'دز 50000 لخالو')
    assert d.chat(1,text,r['conversation_id'])['state']=='DRAFT_PENDING'
    with Session(engine) as s: assert s.get(Draft,r['card']['draft_id']).status=='pending'


def test_two_separate_confirmations(flow,engine):
    d,c=flow; r=d.chat(1,'دز 50000 لخالو وبعدين ادفع الوطنية')
    r=d.chat(1,'أكد',r['conversation_id'])
    assert r['result']['status']=='succeeded' and r['card']['kind']=='bill_payment'
    second=r['card']['draft_id']
    with Session(engine) as s: assert s.get(Draft,second).status=='pending'
    r=d.chat(1,'نعم أكد',r['conversation_id'])
    assert r['result']['status']=='succeeded' and r['state']=='DONE'


def test_duplicate_warning(flow):
    d,c=flow; r=d.chat(1,'دز 1000 لخالو'); c.confirm(1,r['card']['draft_id'])
    r=d.chat(1,'دز 1000 لخالو')
    assert r['card']['duplicate_warning'] and r['card']['amount_words']=='ألف دينار'


def test_only_confirm_can_execute():
    calls=[]
    for path in Path('agent').glob('*.py'):
        tree=ast.parse(path.read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='execute' and isinstance(node.func.value,ast.Attribute) and node.func.value.attr=='wallet':
                calls.append(path.name)
        if path.name not in ['wallet_client.py']:
            assert "'/transfers'" not in path.read_text(encoding='utf-8-sig')
            assert "'/bill-payments'" not in path.read_text(encoding='utf-8-sig')
    assert calls==['confirm.py']
    tree=ast.parse(Path('agent/parser.py').read_text(encoding='utf-8-sig'))
    assert not any(isinstance(n,ast.ImportFrom) and n.module and ('confirm' in n.module or 'wallet_client' in n.module) for n in ast.walk(tree))


def test_wallet_not_reachable_from_outside(engine):
    # The public app must offer no way to pay except /confirm on a card the user saw.
    from app import create_app
    load_seed(engine)
    client=TestClient(create_app(engine))
    r=client.post('/wallet/transfers',headers={'Idempotency-Key':'x1'},json={'user_id':1,'payee_id':8,'amount_iqd':100000})
    assert r.status_code==404 and client.get('/wallet/users/2/balance').status_code==404
    with Session(engine) as s: assert s.scalar(select(func.count()).select_from(Transaction).where(~Transaction.idempotency_key.like('history-%')))==0
