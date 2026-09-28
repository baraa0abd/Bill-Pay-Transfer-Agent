import json
import re
from uuid import uuid4
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .confirm import CONFIRM_TOKENS
from .messages_ar import message
from wallet_api.db import immediate
from wallet_api.models import Conversation, Draft, User, Contact, Bill, UserBiller, Biller, Transaction, now
from wallet_api.idempotency import canonical
from wallet_api.errors import WalletError
from wallet_api.routes import FEE_IQD
from .parser import RuleBasedParser, CANCEL
from .normalize import normalize
from .amounts import parse_amount
from .resolvers import resolve_contact, resolve_biller
from .drafts import create_draft


class Dialogue:
    def __init__(self, engine, parser=None, confirmer=None):
        self.engine,self.parser=engine,parser or RuleBasedParser()
        self.confirmer=confirmer

    def chat(self,user_id,text,conversation_id=None,allow_confirmation=True):
        if allow_confirmation and normalize(text).strip() in CONFIRM_TOKENS and conversation_id and self.confirmer:
            with Session(self.engine) as s:
                convo=s.get(Conversation,conversation_id)
                if not convo or convo.user_id!=user_id: raise WalletError('FORBIDDEN',status=403)
                state=json.loads(convo.state_json)
            if state.get('draft_id') and state['state'] in ['DRAFT_PENDING','EXECUTING']:
                result=self.confirmer.confirm(user_id,state['draft_id'])
                out=self.advance(user_id,conversation_id,state['draft_id'],result)
                out['result']=result
                out['draft_id']=state['draft_id']
                out['messages']=[message(result)]+out.get('messages',[])
                return out
        with immediate(self.engine) as s:
            if not s.get(User,user_id): raise WalletError('UNKNOWN_USER')
            convo=s.get(Conversation,conversation_id) if conversation_id else None
            if conversation_id and (not convo or convo.user_id!=user_id): raise WalletError('FORBIDDEN',status=403)
            if not convo:
                convo=Conversation(id=str(uuid4()),user_id=user_id,state_json=canonical({'state':'IDLE','queue':[]}))
                s.add(convo)
            st=json.loads(convo.state_json); messages=[]
            q=normalize(text).strip()
            if q in CANCEL:
                self.invalidate(s,st,'cancelled')
                if st.get('state')=='EXECUTING':
                    out={'messages':['الطلب قيد التحقق، ما نكدر نلغيه هسه. تابع حالته.'],'state':'EXECUTING','draft_id':st.get('draft_id')}
                else:
                    st={'state':'CANCELLED','queue':[]}
                    out={'messages':['ألغينا الطلب الحالي والباقي. ما انخصم شي للطلبات الملغية؛ أي دفعة سابقة تبقى بالحركات.'],'state':'CANCELLED'}
            elif st['state']=='EXECUTING':
                out={'messages':['دا نتحقق من حالة الدفع. لا تعيد الطلب هسه.'],'state':'EXECUTING','draft_id':st.get('draft_id')}
            elif q=='عرض الاسماء':
                options=[{'id':c.id,'display_name':c.display_name,'masked_phone':'…'+c.phone[-4:],'score':100}
                         for c in s.scalars(select(Contact).where(Contact.user_id==user_id))]
                if st['state']=='FAILED' and st.get('current',{}).get('type')=='transfer':
                    st.pop('payee',None)
                    out=self.question(st,'payee',options)
                else:
                    out={'messages':['جهات اتصالك:']+[o['display_name']+' '+o['masked_phone'] for o in options],'state':st['state']}
            elif re.match(r'لا خليها\s+',q) and st.get('current'):
                self.invalidate(s,st,'superseded')
                st['current']['amount_text']=re.sub(r'^لا خليها\s+','',q)
                st.pop('amount_iqd',None); st.pop('draft_id',None)
                if st.get('ask_slot')=='amount': st.pop('ask_slot',None)
                st['state']='COLLECTING'
                out=self.collect(s,user_id,st)
            elif st['state']=='DRAFT_PENDING':
                draft=s.get(Draft,st['draft_id'])
                out={'messages':['راجع البطاقة واضغط أكّد، أو اكتب أكد.'],'state':'DRAFT_PENDING','card':self.card(draft)}
            elif st.get('ask_slot'):
                slot=st['ask_slot']
                if st.get('options'):
                    options=st['options']; chosen=[]
                    if q.isdigit() and 1<=int(q)<=len(options): chosen=[options[int(q)-1]]
                    else:
                        chosen=[o for o in options if normalize(o['display_name'])==q or (len(q)>=4 and o.get('masked_phone','').endswith(q))]
                    if len(chosen)!=1:
                        out=self.question(st,slot,options)
                    else:
                        st[slot]=chosen[0]; st.pop('ask_slot',None); st.pop('options',None)
                        out=self.collect(s,user_id,st)
                else:
                    st['current'][{'payee':'payee_text','biller':'biller_text','amount':'amount_text'}[slot]]=text
                    st.pop('ask_slot',None)
                    out=self.collect(s,user_id,st)
            else:
                try: intents=self.parser.parse(text)
                except Exception:
                    intents=[]
                if not intents:
                    out={'messages':['ما كدرت أفهم الطلب هسه. اكتب طلبك مرة ثانية، ما انخصم شي.'],'state':'IDLE','code':'PARSER_UNAVAILABLE'}
                else:
                    st={'state':'COLLECTING','queue':[i.model_dump() for i in intents]}
                    if len(intents)>1: messages.append(f'فهمت {len(intents)} طلبات: '+ '، '.join('تحويل' if i.type=='transfer' else 'دفع فاتورة' for i in intents)+' — نبدي بالأول، وكل طلب يحتاج تأكيد وحده.')
                    out=self.next(s,user_id,st)
                out['parser']=getattr(self.parser,'last',None) or 'rules'
            convo.state_json=canonical(st); convo.updated_at=now()
            out['conversation_id']=convo.id
            out['messages']=messages+out.get('messages',[])
            out['queue_remaining']=len(st.get('queue',[]))
            return out

    def voice(self,user_id,transcript,conversation_id=None):
        if transcript.confidence is not None and transcript.confidence>=90 and not transcript.uncertain_tokens:
            out=self.chat(user_id,transcript.text,conversation_id,allow_confirmation=False)
        else:
            with immediate(self.engine) as s:
                if not s.get(User,user_id): raise WalletError('UNKNOWN_USER')
                convo=s.get(Conversation,conversation_id) if conversation_id else None
                if conversation_id and (not convo or convo.user_id!=user_id): raise WalletError('FORBIDDEN',status=403)
                if not convo:
                    convo=Conversation(id=str(uuid4()),user_id=user_id,state_json=canonical({'state':'IDLE','queue':[]}))
                    s.add(convo)
                st=json.loads(convo.state_json)
                self.invalidate(s,st,'superseded')
                if st.get('state')=='EXECUTING':
                    out={'messages':['طلبك السابق قيد التحقق؛ ننتظر نتيجته قبل طلب جديد.'],'state':'EXECUTING','draft_id':st.get('draft_id')}
                else:
                    st={'state':'ASR_REVIEW','queue':[],'transcript':transcript.text}
                    out={'messages':['مو متأكد من الاسم أو المبلغ بالتسجيل. اكتب طلبك الصحيح ويّا الاسم والمبلغ حتى نراجعه. ما نفّذنا طلب جديد.'],
                         'state':'ASR_REVIEW','ask_slot':'transcript'}
                convo.state_json=canonical(st); convo.updated_at=now()
                out['conversation_id']=convo.id
        out['transcript']=transcript.text
        out['confidence']=transcript.confidence
        out['messages']=['هذا اللي سمعته: '+transcript.text]+out.get('messages',[])
        return out

    def invalidate(self,s,st,status):
        if st.get('draft_id'):
            draft=s.get(Draft,st['draft_id'])
            if draft and draft.status=='pending': draft.status=status
            elif draft and draft.status=='confirmed': st['state']='EXECUTING'

    def next(self,s,user_id,st):
        queue=st.get('queue',[])
        st.clear(); st.update(state='COLLECTING',queue=queue)
        if not queue:
            st['state']='DONE'
            return {'messages':['خلصت طلباتك.'],'state':'DONE'}
        st['current']=queue.pop(0)
        return self.collect(s,user_id,st)

    def question(self,st,slot,options=None):
        st['ask_slot']=slot; st['state']='AWAITING_CHOICE' if options else 'COLLECTING'
        if options:
            st['options']=options
            message='تقصد أي واحد؟ '+ '  '.join(f"{i}) {o['display_name']} ({o.get('masked_phone',o.get('account_number',''))})" for i,o in enumerate(options,1))
        else:
            st.pop('options',None)
            message={'payee':'لمن تريد تدز؟ اكتب الاسم الكامل.','biller':'أي فاتورة تريد تدفع؟','amount':'شكد المبلغ بالدينار؟ اكتب الوحدة، مثلاً 50 ألف أو 50 دينار.'}[slot]
        return {'messages':[message],'options':options or [],'ask_slot':slot,'state':st['state']}

    def refuse(self,st,code,message):
        st['state']='FAILED'; st.pop('ask_slot',None); st.pop('options',None)
        return {'messages':[message],'code':code,'state':'FAILED'}

    def collect(self,s,user_id,st):
        intent=st['current']; kind=intent['type']; user=s.get(User,user_id)
        if kind=='balance_inquiry':
            st['state']='DONE'
            messages=[f'رصيدك {user.balance_iqd:,} د.ع.']
            out=self.next(s,user_id,st) if st.get('queue') else {'messages':[],'state':'DONE'}
            return {**out,'messages':messages+out['messages']}
        if kind=='history_inquiry':
            st['state']='DONE'
            txs=list(s.scalars(select(Transaction).where(Transaction.user_id==user_id).order_by(Transaction.created_at.desc()).limit(5)))
            messages=['آخر حركاتك:']+[f'{t.amount_iqd:,} د.ع — {t.id}' for t in txs]
            out=self.next(s,user_id,st) if st.get('queue') else {'messages':[],'state':'DONE'}
            return {**out,'messages':messages+out['messages']}
        if kind in ['unsupported','unclear','cancel']:
            return self.refuse(st,'UNSUPPORTED' if kind=='unsupported' else 'UNCLEAR','ما أگدر أنفذ هالطلب. أگدر أساعدك بتحويل أو دفع فاتورة؛ ما انخصم شي.')
        slot='payee' if kind=='transfer' else 'biller'
        if slot not in st:
            text=intent.get(slot+'_text')
            if not text: return self.question(st,slot)
            result=(resolve_contact if slot=='payee' else resolve_biller)(self.engine,user_id,text)
            if result['status']=='none':
                # «دز 12000 للوطنية» / «ادفع 3000 لريم»: before refusing, see if the name is the other kind.
                other=(resolve_biller if slot=='payee' else resolve_contact)(self.engine,user_id,text)
                if other['status']!='none':
                    if slot=='payee':
                        mobile=s.get(Biller,other['candidates'][0]['biller_id']).category=='mobile_topup'
                        intent.update(type='topup' if mobile else 'bill_payment',biller_text=text,payee_text=None)
                    else: intent.update(type='transfer',payee_text=text,biller_text=None)
                    return self.collect(s,user_id,st)
                return self.refuse(st,'UNKNOWN_PAYEE' if slot=='payee' else 'UNKNOWN_BILLER','ما لگيت هالاسم بحسابك، ما انخصم شي. اكتب الاسم الكامل أو اكتب عرض الأسماء حتى تشوف الموجود.')
            if result['status']=='many': return self.question(st,slot,result['candidates'])
            st[slot]=result['candidates'][0]
        if kind=='topup':
            link=s.get(UserBiller,st['biller']['id'])
            if s.get(Biller,link.biller_id).category!='mobile_topup':
                return self.refuse(st,'UNKNOWN_BILLER','الشحن متوفر لآسياسيل وزين وكورك. ما انخصم شي؛ اختار شبكة الموبايل.')
        if kind=='bill_payment':
            bills=list(s.scalars(select(Bill).where(Bill.user_biller_id==st['biller']['id'],Bill.status=='unpaid').order_by(Bill.period)))
            if not bills: return self.refuse(st,'BILL_ALREADY_PAID','هالفاتورة مدفوعة، ما انخصم شي مرة ثانية.')
            if len(bills)>1 and 'bill' not in st:
                return self.question(st,'bill',[{'id':b.id,'display_name':b.period,'account_number':f'{b.amount_iqd:,} د.ع'} for b in bills])
            bill=s.get(Bill,st['bill']['id']) if 'bill' in st else bills[0]
            amount=bill.amount_iqd
            if intent.get('amount_text'):
                parsed=parse_amount(intent['amount_text'])
                if parsed.ambiguous: return self.question(st,'amount')
                if parsed.value!=amount: return self.refuse(st,'AMOUNT_INVALID',f'مبلغ هالفاتورة {amount:,} د.ع. ما انخصم شي؛ راجع الفاتورة واطلبها من جديد.')
            st['bill_id']=bill.id
        else:
            parsed=parse_amount(intent.get('amount_text'))
            if parsed.ambiguous: return self.question(st,'amount')
            amount=parsed.value
        total=amount+FEE_IQD
        if total>user.balance_iqd:
            return self.refuse(st,'INSUFFICIENT_FUNDS',f'ما تكدر تدفع: تحتاج {total:,} د.ع ويّا العمولة ورصيدك {user.balance_iqd:,} د.ع. ما انخصم شي من حسابك. قلل المبلغ أو زيد رصيدك.')
        spent=s.scalar(select(func.coalesce(func.sum(Transaction.amount_iqd+Transaction.fee_iqd),0)).where(Transaction.user_id==user_id,Transaction.status=='succeeded',Transaction.created_at>=now()//86400*86400))
        if spent+total>user.daily_limit_iqd:
            return self.refuse(st,'LIMIT_EXCEEDED',f'تحتاج {total:,} د.ع والباقي من حدك اليومي {max(0,user.daily_limit_iqd-spent):,} د.ع. ما انخصم شي؛ جرّب مبلغ أقل أو باچر.')
        if kind=='topup':
            bill=Bill(user_biller_id=st['biller']['id'],period='شحن رصيد',amount_iqd=amount,due_date='',status='unpaid')
            s.add(bill); s.flush(); st['bill_id']=bill.id
        payload={'kind':'transfer' if kind=='transfer' else 'bill_payment','payment':{'user_id':user_id,'amount_iqd':amount,
                    'payee_id':st['payee']['id'] if kind=='transfer' else None,'bill_id':st.get('bill_id')},
                 'display':st[slot], 'fee_iqd':FEE_IQD,'balance_before':user.balance_iqd,'balance_after':user.balance_iqd-total,
                 'period':bill.period if kind!='transfer' else None}
        draft=create_draft(s,user_id,payload)
        st['draft_id']=draft.id; st['state']='DRAFT_PENDING'; st.pop('ask_slot',None); st.pop('options',None)
        return {'messages':['راجع التفاصيل قبل التأكيد. ما انخصم شي لحد هسه.'],'state':'DRAFT_PENDING','card':self.card(draft)}

    def card(self,draft):
        payload=json.loads(draft.payload_json)
        return {'draft_id':draft.id,'expires_at':draft.expires_at,**payload}

    def advance(self,user_id,conversation_id,draft_id,result):
        with immediate(self.engine) as s:
            convo=s.get(Conversation,conversation_id)
            if not convo or convo.user_id!=user_id: raise WalletError('FORBIDDEN',status=403)
            st=json.loads(convo.state_json)
            if st.get('draft_id')!=draft_id:
                return {'messages':[],'state':st['state'],'conversation_id':convo.id}
            if result.get('code')=='STATUS_UNKNOWN':
                st['state']='EXECUTING'; out={'messages':[],'state':'EXECUTING'}
            elif result.get('status')=='succeeded':
                out=self.next(s,user_id,st)
            else:
                st['state']='FAILED'; out={'messages':[],'state':'FAILED'}
            convo.state_json=canonical(st); convo.updated_at=now()
            return {**out,'conversation_id':convo.id}
