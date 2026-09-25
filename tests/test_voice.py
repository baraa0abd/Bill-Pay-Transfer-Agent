import pytest
import httpx
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app import create_app
from data.seed import load_seed
from wallet_api.models import Draft,Transaction
from voice.asr import MockASR,WhisperClient

@pytest.mark.parametrize('confidence,uncertain',[(40,[]),(None,[]),(99,['حسن'])])
def test_misheard_name_forces_review(engine,confidence,uncertain):
    load_seed(engine)
    web=TestClient(create_app(engine,asr=MockASR('دز 50000 لحسن',confidence,uncertain)),headers={'X-User-ID':'1'})
    r=web.post('/voice',data={'user_id':'1'},files={'audio':('test.wav',b'mock','audio/wav')}).json()
    assert r['transcript']=='دز 50000 لحسن' and r['ask_slot']=='transcript'
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(Draft))==0


def test_voice_confirm_never_executes(engine):
    load_seed(engine)
    web=TestClient(create_app(engine,asr=MockASR('أكد')),headers={'X-User-ID':'1'})
    r=web.post('/chat',json={'user_id':1,'text':'دز 50000 لخالو'}).json();key=r['card']['draft_id']
    r=web.post('/voice',data={'user_id':'1','conversation_id':r['conversation_id']},files={'audio':('test.webm',b'mock','audio/webm')}).json()
    assert r['state']=='DRAFT_PENDING'
    with Session(engine) as s:
        assert s.get(Draft,key).status=='pending'
        assert s.scalar(select(func.count()).select_from(Transaction).where(Transaction.idempotency_key==key))==0


def test_review_then_corrected_text(engine):
    load_seed(engine)
    web=TestClient(create_app(engine,asr=MockASR('دز 50000 لحسن',20)),headers={'X-User-ID':'1'})
    r=web.post('/voice',data={'user_id':'1'},files={'audio':('test.wav',b'mock','audio/wav')}).json()
    r=web.post('/chat',json={'user_id':1,'text':'دز 50000 لخالو','conversation_id':r['conversation_id']}).json()
    assert r['card']['payment']['payee_id']==8


def test_hosted_contract_unknown_confidence():
    def respond(request):
        assert request.url.path=='/v1/audio/transcriptions'
        return httpx.Response(200,json={'text':'دز خمسين ألف لخالو'})
    asr=WhisperClient('mock',transport=httpx.Client(transport=httpx.MockTransport(respond)))
    transcript=asr.transcribe(b'mock','voice.wav','audio/wav')
    assert transcript.confidence is None


def test_bad_audio(engine):
    load_seed(engine)
    web=TestClient(create_app(engine,asr=MockASR('مرحبا')),headers={'X-User-ID':'1'})
    assert web.post('/voice',data={'user_id':'1'},files={'audio':('x.txt',b'mock','text/plain')}).status_code==400
