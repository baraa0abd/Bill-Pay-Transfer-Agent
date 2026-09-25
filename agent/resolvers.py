from rapidfuzz.fuzz import ratio, token_set_ratio
from sqlalchemy import select
from sqlalchemy.orm import Session
from wallet_api.models import Contact, Biller, UserBiller
from .normalize import normalize


def rank(candidates):
    candidates.sort(key=lambda x: (-x['score'], x['id']))
    if not candidates:
        return {'status':'none','candidates':[]}
    certain = candidates[0].get('exact', True) and candidates[0]['score'] >= 90 and (len(candidates) == 1 or candidates[0]['score'] - candidates[1]['score'] >= 15)
    return {'status':'one' if certain else 'many','candidates':candidates[:1] if certain else candidates}


def resolve_contact(engine, user_id, text):
    q = normalize(text)
    if not q: return rank([])
    candidates=[]
    with Session(engine) as s:
        for c in s.scalars(select(Contact).where(Contact.user_id == user_id)):
            values = [normalize(c.display_name), normalize(c.nickname or '')]
            score = 0
            for name in filter(None, values):
                if q == name: current = 100
                elif q in name.split() or name.startswith(q+' '): current = 92
                else: current = round(ratio(q,name))
                score = max(score,current)
            if score >= 80:
                candidates.append({'id':c.id,'display_name':c.display_name,'masked_phone':'…'+c.phone[-4:],'score':score,'exact':q in values})
    return rank(candidates)


def resolve_biller(engine, user_id, text):
    q = normalize(text)
    categories=[]
    provider=None
    if 'وطني' in q: categories=['electricity_national']
    elif 'مولد' in q: categories=['generator']
    elif 'كهرب' in q: categories=['electricity_national','generator']
    elif any(w in q for w in ['انترنت','النت','نت','إنترنت']): categories=['internet']
    elif any(w in q for w in ['ماء','ماي']): categories=['water']
    elif any(w in q for w in ['رصيد','شحن','اسيا','زين','كورك']):
        categories=['mobile_topup']
        provider=next((p for w,p in [('اسيا','asiacell'),('زين','zain'),('كورك','korek')] if w in q),None)
    with Session(engine) as s:
        candidates=[{'id':u.id,'biller_id':b.id,'display_name':b.name_ar,'account_number':u.account_number,'score':100}
            for b,u in s.execute(select(Biller,UserBiller).join(UserBiller).where(UserBiller.user_id == user_id))
            if (b.category in categories and (provider is None or b.provider == provider)) or normalize(b.name_ar) == q]
    return rank(candidates)

