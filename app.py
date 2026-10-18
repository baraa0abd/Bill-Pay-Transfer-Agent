import json
import os
from pathlib import Path
from fastapi import FastAPI, Header, File, Form, UploadFile
from starlette.concurrency import run_in_threadpool
from voice.asr import WhisperClient
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from wallet_api.db import make_engine, Base
from wallet_api.models import User, Conversation, Draft
from wallet_api.schemas import ChatRequest, DraftRequest
from wallet_api.errors import WalletError, install_errors
from wallet_api.routes import create_wallet, record
from wallet_api.transport import LocalWalletTransport
from agent.wallet_client import WalletClient
from agent.confirm import Confirmer
from agent.dialogue import Dialogue
from agent.parser import configured_parser
from agent.messages_ar import message
from agent.env import load_env

ROOT=Path(__file__).resolve().parent


def create_app(engine=None,parser=None,demo_mode=None,asr=None,llm_max_wait=None):
    engine=engine or make_engine()
    Base.metadata.create_all(engine)
    demo_mode=demo_mode if demo_mode is not None else os.getenv('DEMO_MODE','false').lower()=='true'
    app=FastAPI(title='Bill Pay & Transfer Agent')
    install_errors(app)
    wallet_app=create_wallet(engine,demo_mode)
    transport=LocalWalletTransport(wallet_app)
    confirmer=Confirmer(engine,WalletClient(transport))
    dialogue=Dialogue(engine,parser=parser or configured_parser(max_wait=llm_max_wait),confirmer=confirmer)
    asr_client=asr or WhisperClient()
    app.state.engine=engine; app.state.dialogue=dialogue; app.state.confirmer=confirmer
    app.mount('/wallet',wallet_app)

    @app.get('/')
    def index(): return FileResponse(ROOT/'ui'/'index.html')

    @app.get('/users')
    def users():
        with Session(engine) as s:
            return [{'id':u.id,'name':u.name} for u in s.scalars(select(User))]

    @app.get('/config')
    def config(): return {'demo_mode':demo_mode,'voice_enabled':asr is not None or bool(os.getenv('ASR_API_KEY'))}

    @app.get('/account')
    def account(x_user_id:int=Header()):
        balance=transport.get(f'/users/{x_user_id}/balance')
        if balance.status_code!=200: raise WalletError('UNKNOWN_USER')
        return {'balance':balance.json(),'transactions':transport.get(f'/users/{x_user_id}/transactions').json()}

    @app.post('/chat')
    def chat(body:ChatRequest,x_user_id:int=Header()):
        if body.user_id!=x_user_id: raise WalletError('FORBIDDEN',status=403)
        return dialogue.chat(x_user_id,body.text,body.conversation_id)

    def attach_followup(user_id,draft_id,result):
        with Session(engine) as s:
            convo=next((c for c in s.scalars(select(Conversation).where(Conversation.user_id==user_id))
                        if json.loads(c.state_json).get('draft_id')==draft_id),None)
            cid=convo.id if convo else None
        out=dialogue.advance(user_id,cid,draft_id,result) if cid else {'messages':[]}
        return {**out,'messages':[message(result)]+out.get('messages',[]),'result':result,'draft_id':draft_id}

    @app.post('/confirm')
    def confirm(body:DraftRequest,x_user_id:int=Header(),x_fault:str|None=Header(default=None)):
        result=confirmer.confirm(x_user_id,body.draft_id,x_fault if demo_mode else None)
        return attach_followup(x_user_id,body.draft_id,result)

    @app.post('/cancel')
    def cancel(body:DraftRequest,x_user_id:int=Header()):
        result=confirmer.cancel(x_user_id,body.draft_id)
        return {'messages':[message(result)],'result':result,'state':'EXECUTING' if result['code']=='STATUS_UNKNOWN' else 'CANCELLED'}

    @app.get('/drafts/{draft_id}/status')
    def status(draft_id:str,x_user_id:int=Header()):
        result=confirmer.status(x_user_id,draft_id)
        if result.get('code')=='DRAFT_PENDING':
            with Session(engine) as s:
                draft=s.get(Draft,draft_id)
                return {'messages':[message(result)],'result':result,'state':'DRAFT_PENDING','card':dialogue.card(draft)}
        return attach_followup(x_user_id,draft_id,result)

    @app.get('/conversations/{conversation_id}')
    def conversation(conversation_id:str,x_user_id:int=Header()):
        with Session(engine) as s:
            convo=s.get(Conversation,conversation_id)
            if not convo or convo.user_id!=x_user_id: raise WalletError('FORBIDDEN',status=403)
            state=json.loads(convo.state_json)
            out={'conversation_id':convo.id,'state':state['state'],'messages':[],'options':state.get('options',[]),'ask_slot':state.get('ask_slot')}
            if state.get('draft_id'):
                draft=s.get(Draft,state['draft_id'])
                if draft.status=='pending': out['card']=dialogue.card(draft)
                elif draft.status=='confirmed': out['draft_id']=draft.id
            return out

    @app.post('/voice')
    async def voice(audio:UploadFile=File(),user_id:int=Form(),conversation_id:str|None=Form(default=None),x_user_id:int=Header()):
        if user_id!=x_user_id: raise WalletError('FORBIDDEN',status=403)
        if audio.content_type not in ['audio/webm','audio/wav','audio/x-wav']:
            return JSONResponse({'code':'ASR_INVALID','messages':['صيغة الصوت مو مدعومة. استخدم تسجيل ويب أو ملف ويف؛ ما نفّذنا طلب جديد.']},status_code=400)
        contents=await audio.read(8*1024*1024+1)
        await audio.close()
        if not contents or len(contents)>8*1024*1024:
            return JSONResponse({'code':'ASR_INVALID','messages':['التسجيل فارغ أو طويل هواية. جرّب تسجيل أقصر؛ ما نفّذنا طلب جديد.']},status_code=400)
        try: transcript=await run_in_threadpool(asr_client.transcribe,contents,audio.filename or 'recording.webm',audio.content_type)
        except Exception:
            return JSONResponse({'code':'ASR_UNAVAILABLE','messages':['ما كدرنا نسمع التسجيل هسه. اكتب طلبك؛ ما نفّذنا طلب جديد.']},status_code=503)
        return await run_in_threadpool(dialogue.voice,user_id,transcript,conversation_id)

    return app


load_env()  # .env keys and LLM_PROVIDER for the running server
# A person is waiting: if the model is busy for more than 3 s, the rule parser answers (the badge says so).
app=create_app(llm_max_wait=float(os.getenv('LLM_MAX_WAIT','3')))
