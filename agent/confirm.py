"""The sole agent call site authorized to invoke WalletClient.execute."""
import json
import hmac
from sqlalchemy import select
from wallet_api.db import immediate
from wallet_api.models import Draft, Conversation, now
from wallet_api.idempotency import digest, canonical
from wallet_api.schemas import Payment

CONFIRM_TOKENS = {'اكد','تاكيد','نعم اكد'}


class Confirmer:
    def __init__(self,engine,wallet):
        self.engine,self.wallet=engine,wallet

    def confirm(self,user_id,draft_id,fault=None):
        with immediate(self.engine) as s:
            draft=s.get(Draft,draft_id)
            if not draft or draft.user_id!=user_id: return {'code':'DRAFT_FORBIDDEN'}
            if draft.status not in ['pending','confirmed']: return {'code':'DRAFT_'+draft.status.upper()}
            payload=json.loads(draft.payload_json)
            if not hmac.compare_digest(digest(payload),draft.content_hash): return {'code':'DRAFT_TAMPERED'}
            try: payment=Payment.model_validate(payload['payment'])
            except (ValueError,KeyError): return {'code':'DRAFT_TAMPERED'}
            if payment.user_id!=user_id or payload['kind'] not in ['transfer','bill_payment']: return {'code':'DRAFT_TAMPERED'}
            if draft.result_json:
                result=json.loads(draft.result_json)
                if result.get('code')!='STATUS_UNKNOWN': return result
            if draft.status=='pending':
                if now()>=draft.expires_at:
                    draft.status='expired'
                    return {'code':'DRAFT_EXPIRED'}
                draft.status='confirmed'
                for convo in s.scalars(select(Conversation).where(Conversation.user_id==user_id)):
                    state=json.loads(convo.state_json)
                    if state.get('draft_id')==draft_id:
                        state['state']='EXECUTING'; convo.state_json=canonical(state)
        # Durable authorization precedes network I/O. Retries of this confirmed operation
        # reuse its immutable UUID, including recovery after a process crash.
        result=self.wallet.execute(payload['kind'],payment.model_dump(),draft_id,fault)
        if result.get('status')=='succeeded':
            result={**result,'payee_name':payload['display']['display_name']}
        with immediate(self.engine) as s:
            draft=s.get(Draft,draft_id)
            previous=json.loads(draft.result_json) if draft.result_json else None
            if previous and previous.get('code')!='STATUS_UNKNOWN': return previous
            draft.result_json=canonical(result)
        return result

    def cancel(self,user_id,draft_id):
        with immediate(self.engine) as s:
            draft=s.get(Draft,draft_id)
            if not draft or draft.user_id!=user_id: return {'code':'DRAFT_FORBIDDEN'}
            if draft.status=='confirmed': return {'code':'STATUS_UNKNOWN'}
            if draft.status=='pending': draft.status='cancelled'
            for convo in s.scalars(select(Conversation).where(Conversation.user_id==user_id)):
                state=json.loads(convo.state_json)
                if state.get('draft_id')==draft_id:
                    convo.state_json=canonical({'state':'CANCELLED','queue':[]})
            return {'code':'CANCELLED'}

    def status(self,user_id,draft_id):
        with immediate(self.engine) as s:
            draft=s.get(Draft,draft_id)
            if not draft or draft.user_id!=user_id: return {'code':'DRAFT_FORBIDDEN'}
            if draft.status!='confirmed': return {'code':'DRAFT_'+draft.status.upper()}
            previous=json.loads(draft.result_json) if draft.result_json else None
            if previous and previous.get('code')!='STATUS_UNKNOWN': return previous
        result=self.wallet.lookup(user_id,draft_id)
        if result.get('status')=='succeeded':
            with immediate(self.engine) as s:
                draft=s.get(Draft,draft_id)
                result['payee_name']=json.loads(draft.payload_json)['display']['display_name']
                draft.result_json=canonical(result)
        return result
