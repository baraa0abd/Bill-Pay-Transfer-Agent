import json
import os
from pathlib import Path
from fastapi import FastAPI, Header
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

ROOT=Path(__file__).resolve().parent


def create_app(engine=None,parser=None,demo_mode=None):
    engine=engine or make_engine()
    Base.metadata.create_all(engine)
    demo_mode=demo_mode if demo_mode is not None else os.getenv('DEMO_MODE','false').lower()=='true'
    app=FastAPI(title='Bill Pay & Transfer Agent')
    install_errors(app)
    wallet_app=create_wallet(engine,demo_mode)
    transport=LocalWalletTransport(wallet_app)
    confirmer=Confirmer(engine,WalletClient(transport))
    dialogue=Dialogue(engine,parser=parser or configured_parser(),confirmer=confirmer)
    app.state.engine=engine; app.state.dialogue=dialogue; app.state.confirmer=confirmer
    app.mount('/wallet',wallet_app)

    @app.get('/')
    def index(): return FileResponse(ROOT/'ui'/'index.html')

    @app.get('/users')
    def users():
        with Session(engine) as s:
            return [{'id':u.id,'name':u.name} for u in s.scalars(select(User))]

    @app.get('/config')
    def config(): return {'demo_mode':demo_mode,'voice_enabled':bool(os.getenv('ASR_API_KEY'))}

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
        return attach_followup(x_user_id,draft_id,confirmer.status(x_user_id,draft_id))

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

    return app


app=create_app()
