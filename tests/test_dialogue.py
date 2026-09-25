import json
import pytest
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from data.seed import load_seed
from agent.dialogue import Dialogue
from wallet_api.models import Draft,Transaction,Conversation

@pytest.fixture
def dialogue(engine):
    load_seed(engine)
    return Dialogue(engine)


def test_ahmed(dialogue,engine):
    r=dialogue.chat(1,'دز خمسين ألف لأحمد')
    assert len(r['options'])==3 and r['ask_slot']=='payee'
    r=dialogue.chat(1,'2',r['conversation_id'])
    assert r['card']['payment']['payee_id']==2
    assert r['card']['payment']['amount_iqd']==50000


def test_electricity(dialogue):
    r=dialogue.chat(1,'ادفع الكهرباء')
    assert len(r['options'])==2 and r['ask_slot']=='biller'


def test_cancel(dialogue,engine):
    r=dialogue.chat(1,'دز 50000 لخالو')
    r=dialogue.chat(1,'بطلت',r['conversation_id'])
    assert r['state']=='CANCELLED'
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(Draft).where(Draft.status=='pending'))==0


def test_insufficient(dialogue,engine):
    r=dialogue.chat(1,'دز نص مليون لخالو')
    assert r['code']=='INSUFFICIENT_FUNDS'
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(Draft))==0


def test_restart(dialogue,engine):
    r=dialogue.chat(1,'دز خمسين ألف لأحمد')
    replacement=Dialogue(engine)
    assert replacement.chat(1,'1234',r['conversation_id'])['card']['payment']['payee_id']==2


def test_queue(dialogue,engine):
    r=dialogue.chat(1,'دز 50000 لخالو وبعدين سدد الوطنية')
    assert r['queue_remaining']==1 and r['card']['kind']=='transfer'
    with Session(engine) as s:
        state=json.loads(s.get(Conversation,r['conversation_id']).state_json)
        assert state['queue'][0]['type']=='bill_payment'


def test_edit(dialogue,engine):
    r=dialogue.chat(1,'دز 50000 لخالو'); old=r['card']['draft_id']
    r=dialogue.chat(1,'لا خليها ثلاثين ألف',r['conversation_id'])
    assert r['card']['payment']['amount_iqd']==30000
    with Session(engine) as s: assert s.get(Draft,old).status=='superseded'


def test_amount_question(dialogue):
    r=dialogue.chat(1,'دز خمسين لخالو')
    assert r['ask_slot']=='amount'
    r=dialogue.chat(1,'50 ألف',r['conversation_id'])
    assert r['card']['payment']['amount_iqd']==50000
