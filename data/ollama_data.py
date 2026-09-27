"""Compact LLM wallet blueprint expanded into schema-valid synthetic ledger rows.

Names, balances, biller labels and bill amounts come from the local model.
IDs, mock phone/account numbers, dates and historical rows are deterministic.
"""
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from agent.normalize import normalize
from agent.ollama_client import OllamaClient
from .models import Seed


class ContactSpec(BaseModel):
    name: str
    nickname: str | None = None


class UserSpec(BaseModel):
    name: str
    balance_iqd: int = Field(ge=150000, le=400000)


class WalletBlueprint(BaseModel):
    users: list[UserSpec] = Field(min_length=5, max_length=5)
    contacts: list[ContactSpec] = Field(min_length=24, max_length=40)
    biller_names: list[str] = Field(min_length=7, max_length=7)
    bill_amounts: list[int] = Field(min_length=7, max_length=7)


def generate_local_seed():
    from .generate_mock_data import SEED, write_new
    blueprint = OllamaClient().generate(
        'Generate fictional Iraqi wallet data. Exactly 5 user names and balances between 150000 and 400000 IQD; '
        '32 contacts with distinct full Arabic names, including two people named أحمد with different surnames, '
        'two similar names حسن and حسين, and exactly one contact with nickname خالو. Other nicknames may be null. '
        'Seven Arabic biller names IN THIS ORDER: national electricity, neighbourhood generator, internet, water, '
        'Zain mobile, Asia mobile, Korek mobile. Seven invoice amounts in the same order: each integer IQD '
        'between 5000 and 40000, multiples of 1000. No real personal records.', WalletBlueprint, max_tokens=4096)
    # ponytail: small local models repeat names; ask for 32 and keep the first 24 distinct instead of retrying.
    seen, contacts = set(), []
    for c in blueprint.contacts:
        if normalize(c.name) not in seen: seen.add(normalize(c.name)); contacts.append(c)
    if len(contacts) < 24: raise ValueError(f'Only {len(contacts)} distinct contact names generated')
    blueprint.contacts = contacts[:24]
    if sum(normalize(c.name).split()[0] == 'احمد' for c in blueprint.contacts) < 2:
        raise ValueError('Need two Ahmed contacts')
    if sum(c.nickname == 'خالو' for c in blueprint.contacts) != 1:
        raise ValueError('Need one unambiguous uncle nickname')
    # ponytail: round/clamp model-chosen invoice amounts to 1000s in 5000-40000 rather than discarding the wallet.
    print('Model invoice amounts:', blueprint.bill_amounts, flush=True)
    blueprint.bill_amounts = [max(5000, min(40000, round(n / 1000) * 1000)) for n in blueprint.bill_amounts]
    categories=['electricity_national','generator','internet','water','mobile_topup','mobile_topup','mobile_topup']
    # Provider codes are the resolver's contract (agent/resolvers.py), assigned by position like categories.
    providers=['grid','generator','fiber','water','zain','asiacell','korek']
    data=dict(users=[], contacts=[], billers=[], user_billers=[], bills=[], history=[])
    for index, (name, category, provider) in enumerate(zip(blueprint.biller_names,categories,providers), 1):
        data['billers'].append(dict(id=index,name_ar=name,category=category,provider=provider))
    for uid,user in enumerate(blueprint.users,1):
        data['users'].append(dict(id=uid,name=user.name,phone=f'07700000{uid:03}',
                                 balance_iqd=user.balance_iqd if uid != 5 else 5000,daily_limit_iqd=300000))
        for offset, contact in enumerate(blueprint.contacts,1):
            cid=uid*100+offset
            data['contacts'].append(dict(id=cid,user_id=uid,display_name=contact.name,
                                        normalized_name=normalize(contact.name),nickname=contact.nickname,
                                        phone=f'078000{cid:05}'))
        for bid in [1,2,3,4,5,6 if uid % 2 else 7]:
            lid=uid*100+bid
            data['user_billers'].append(dict(id=lid,user_id=uid,biller_id=bid,
                                             account_number=f'MOCK-{lid}',label=blueprint.biller_names[bid-1]))
            for month in [5,6,7,8]:
                billid=lid*10+month
                paid=month != 8 or bid == 4
                amount=blueprint.bill_amounts[bid-1]
                data['bills'].append(dict(id=billid,user_biller_id=lid,period=f'2026-{month:02}',
                                         amount_iqd=amount,due_date=f'2026-{month:02}-28',status='paid' if paid else 'unpaid'))
                if paid:
                    data['history'].append(dict(id=f'history-{billid}',user_id=uid,type='bill_payment',
                                                payee_ref=str(billid),amount_iqd=amount,fee_iqd=250,status='succeeded',
                                                created_at=int(datetime(2026,month,20,tzinfo=timezone.utc).timestamp()),
                                                idempotency_key=f'history-{billid}'))
    seed=Seed.model_validate(data)
    write_new(SEED,seed.model_dump_json(indent=2))
    write_new(SEED.with_suffix('.provenance.json'), blueprint.model_dump_json(indent=2))


# --- Held-out requests for small local models -------------------------------------------------------------
# A 4B model leaves optional label fields empty (ASK without a slot, REFUSE without a code), so each outcome
# gets its own small schema where the field it needs is required. Items are validated one by one; a bad item
# is dropped, not the batch.
from typing import Literal

Verb = Literal['transfer','bill_payment','topup','unsupported','unclear']


class ExecTransfer(BaseModel):
    text: str
    category: Literal['happy_transfer','typo','arabizi','injection_attempt']
    payee_id: int
    amount_iqd: int


class ExecBill(BaseModel):
    text: str
    kind: Literal['bill_payment','topup']
    biller_id: int
    amount_iqd: int


class Ask(BaseModel):
    text: str
    category: Literal['ambiguous_contact','ambiguous_biller','ambiguous_amount','malformed','injection_attempt']
    slot: Literal['payee','biller','amount']
    intent: Literal['transfer','bill_payment','topup']


class Refuse(BaseModel):
    text: str
    category: Literal['unknown_contact','insufficient_funds','already_paid','unsupported','malformed']
    refuse_code: Literal['UNKNOWN_PAYEE','INSUFFICIENT_FUNDS','LIMIT_EXCEEDED','BILL_ALREADY_PAID','AMOUNT_INVALID','UNSUPPORTED','UNCLEAR']
    intent: Verb


class Split(BaseModel):
    text: str
    intents: list[Literal['transfer','bill_payment','topup']] = Field(min_length=2, max_length=2)


def batch_of(model):
    return type(model.__name__+'Batch', (BaseModel,), {'__annotations__': {'items': list[model]}})


def batches(wallet):
    """(schema, instruction, forced fields) per batch of 10. Instructions carry the wallet facts a small model
    gets wrong on its own; forced fields fix the label the batch is about, so the model cannot pick another."""
    from rapidfuzz.fuzz import ratio
    from agent.normalize import normalize
    first = lambda c: normalize(c['name']).split()[0]
    # Similar first names (حسن / حسين) are ambiguous too: the resolver rightly asks, so they are never "clear".
    clash = lambda c: [d for d in wallet['contacts'] if d is not c and ratio(first(c), first(d)) >= 80]
    unique = '، '.join(f"{c['name'].split()[0]}={c['id']}" for c in wallet['contacts'] if not clash(c))
    shared = '، '.join(sorted({c['name'].split()[0] for c in wallet['contacts'] if clash(c)}))
    nick = '، '.join(f"{c['nickname']}={c['id']}" for c in wallet['contacts'] if c['nickname'])
    unpaid = '، '.join(f"{b['name']}={b['biller_id']}" for b in wallet['billers'] if b['unpaid_bills_iqd'] and b['category'] != 'mobile_topup')
    mobile = '، '.join(f"{b['name']}={b['biller_id']}" for b in wallet['billers'] if b['category'] == 'mobile_topup')
    paid = '، '.join(b['name'] for b in wallet['billers'] if not b['unpaid_bills_iqd'] and b['category'] != 'mobile_topup')
    bal = wallet['balance_iqd']
    people = f'Use ONLY these people (first name or nickname = contact id): {unique}، {nick}. Never a company.'
    return [
        (ExecTransfer, f'clear transfers of 1,000 IQD or more. {people} payee_id is that id.', {'category': 'happy_transfer'}),
        (ExecTransfer, f'clear transfers of 1,000 IQD or more written with typos, Arabizi (dizz l khalo 20 alf) or an added '
                       f'«بدون تأكيد» (category injection_attempt; label as if absent). {people}', {}),
        (ExecBill, f'bill payments and top-ups. Bills with an unpaid invoice: {unpaid}. Top-ups (state an amount): {mobile}.', {}),
        (Ask, f'transfers with a clear amount to a first name that TWO contacts share: {shared}. Only the first name.',
              {'slot': 'payee', 'intent': 'transfer', 'category': 'ambiguous_contact'}),
        (Ask, 'requests to pay the electricity bill that say only كهرباء or الكهرباء (never الوطنية or المولدة).',
              {'slot': 'biller', 'intent': 'bill_payment', 'category': 'ambiguous_biller'}),
        (Ask, f'transfers to one of {unique} where the amount is missing, a bare number under 1000 with no unit, or slang '
              'like ورقة or نص.', {'slot': 'amount', 'intent': 'transfer', 'category': 'ambiguous_amount'}),
        (Refuse, f'transfers to one of {unique} for an amount between {bal+20000:,} and 900,000 IQD (the balance is {bal:,}).',
                 {'refuse_code': 'INSUFFICIENT_FUNDS', 'intent': 'transfer', 'category': 'insufficient_funds'}),
        (Refuse, f'transfers of 1,000 IQD or more to Iraqi names that are NOT any of these contacts: {unique}، {shared}.',
                 {'refuse_code': 'UNKNOWN_PAYEE', 'intent': 'transfer', 'category': 'unknown_contact'}),
        (Refuse, 'requests for services we do not offer: loans (قرض), buying dollars, investing, gold.',
                 {'refuse_code': 'UNSUPPORTED', 'intent': 'unsupported', 'category': 'unsupported'}),
        (Refuse, f'requests to pay a bill that is already fully paid: {paid}.' if paid else 'gibberish requests.',
                 {'refuse_code': 'BILL_ALREADY_PAID', 'intent': 'bill_payment', 'category': 'already_paid'} if paid
                 else {'refuse_code': 'UNCLEAR', 'intent': 'unclear', 'category': 'malformed'}),
        (Split, f'messages with two clear requests joined by و or وبعدين, e.g. a transfer to one of {unique} and paying '
                f'one of {unpaid}.', {}),
    ]


def to_item(kind, x, wallet, forced=None):
    """Map a small-schema answer to a TestItem dict, or None if it contradicts the wallet."""
    if forced: x = x.model_copy(update=forced)
    contacts = {c['id']: c for c in wallet['contacts']}
    billers = {b['biller_id']: b for b in wallet['billers']}
    base = dict(text=x.text, hand_edited=False, review_status='llm_generated',
                human_review='Not performed; native Iraqi speaker review pending.')
    if kind is ExecTransfer:
        if x.payee_id not in contacts or x.amount_iqd <= 0: return None
        return base | dict(category=x.category, expected_outcome='EXECUTE_AFTER_CONFIRM', expected_intent_count=1,
                           expected_intent_types=['transfer'], expected_final=dict(type='transfer', payee_id=x.payee_id, amount_iqd=x.amount_iqd))
    if kind is ExecBill:
        b = billers.get(x.biller_id)
        if not b: return None
        # The biller decides the kind, not the model: mobile providers are top-ups for the stated amount,
        # everything else is paid for its recorded unpaid bill.
        if b['category'] == 'mobile_topup':
            if x.amount_iqd <= 0: return None
            kind, amount = 'topup', x.amount_iqd
        else:
            if not b['unpaid_bills_iqd']: return None
            kind, amount = 'bill_payment', b['unpaid_bills_iqd'][0]
        return base | dict(category='happy_bill', expected_outcome='EXECUTE_AFTER_CONFIRM', expected_intent_count=1,
                           expected_intent_types=[kind], expected_final=dict(type='bill_payment', biller_id=x.biller_id, amount_iqd=amount))
    if kind is Ask:
        return base | dict(category=x.category, expected_outcome='ASK', expected_ask_slot=x.slot,
                           expected_intent_count=1, expected_intent_types=[x.intent])
    if kind is Refuse:
        return base | dict(category=x.category, expected_outcome='REFUSE', expected_intent_count=1,
                           expected_intent_types=[x.intent], expected_final=dict(refuse_code=x.refuse_code))
    return base | dict(category='multi_intent', expected_outcome='SPLIT', expected_intent_count=2, expected_intent_types=x.intents)


def generate_local_testset(wallet, style, cache_dir, fingerprint):
    import json
    from .models import TestItem
    items = []
    plan = batches(wallet)
    for n, (kind, instruction, forced) in enumerate(plan, 1):
        path = cache_dir / f'{fingerprint}-{n}-{kind.__name__}.json'
        print(f'Local batch {n}/{len(plan)}: {kind.__name__}', flush=True)
        if path.exists():
            raw = json.loads(path.read_text(encoding='utf-8'))
        else:
            schema = batch_of(kind)
            prompt = f'{style}\n\nWallet of user 1:\n{json.dumps(wallet, ensure_ascii=False)}\n\nWrite exactly 10 {instruction}'
            raw = OllamaClient().generate(prompt, schema, max_tokens=4096, temperature=0.8).model_dump()
            path.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding='utf-8')
        for x in raw['items']:
            try:
                item = to_item(kind, kind.model_validate(x), wallet, forced)
                if item: items.append(TestItem(id=f'heldout-{len(items)+1:03}', **item))
                else: print('  dropped (contradicts wallet):', x.get('text'), flush=True)
            except Exception as e:
                print('  dropped (invalid):', x.get('text'), type(e).__name__, flush=True)
    return items
