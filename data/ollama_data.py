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
    contacts: list[ContactSpec] = Field(min_length=24, max_length=24)
    biller_names: list[str] = Field(min_length=7, max_length=7)
    bill_amounts: list[int] = Field(min_length=7, max_length=7)


def generate_local_seed():
    from .generate_mock_data import SEED, write_new
    blueprint = OllamaClient().generate(
        'Generate fictional Iraqi wallet data. Exactly 5 user names and balances between 150000 and 400000 IQD; '
        '24 contacts with distinct full Arabic names, including two people named أحمد with different surnames, '
        'two similar names حسن and حسين, and exactly one contact with nickname خالو. Other nicknames may be null. '
        'Seven Arabic biller names IN THIS ORDER: national electricity, neighbourhood generator, internet, water, '
        'Zain mobile, Asia mobile, Korek mobile. Seven invoice amounts in the same order: each integer IQD '
        'between 5000 and 40000, multiples of 1000. No real personal records.', WalletBlueprint, max_tokens=4096)
    if len({normalize(c.name) for c in blueprint.contacts}) != 24:
        raise ValueError('Generated contact full names must be distinct')
    if sum(normalize(c.name).split()[0] == 'احمد' for c in blueprint.contacts) < 2:
        raise ValueError('Need two Ahmed contacts')
    if sum(c.nickname == 'خالو' for c in blueprint.contacts) != 1:
        raise ValueError('Need one unambiguous uncle nickname')
    if any(not 5000 <= n <= 40000 or n % 1000 for n in blueprint.bill_amounts):
        raise ValueError('Invalid generated invoice amounts')
    categories=['electricity_national','generator','internet','water','mobile_topup','mobile_topup','mobile_topup']
    data=dict(users=[], contacts=[], billers=[], user_billers=[], bills=[], history=[])
    for index, (name, category) in enumerate(zip(blueprint.biller_names,categories), 1):
        data['billers'].append(dict(id=index,name_ar=name,category=category,provider=f'mock-provider-{index}'))
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
