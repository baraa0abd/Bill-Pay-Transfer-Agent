from typing import Literal
from pydantic import Field, model_validator
from wallet_api.schemas import StrictModel


class SeedUser(StrictModel):
    id: int
    name: str
    phone: str
    balance_iqd: int = Field(ge=0)
    daily_limit_iqd: int = Field(gt=0)
    pin_hash: str | None = None


class SeedContact(StrictModel):
    id: int
    user_id: int
    display_name: str
    normalized_name: str
    nickname: str | None = None
    phone: str


class SeedBiller(StrictModel):
    id: int
    name_ar: str
    category: Literal['electricity_national','generator','internet','mobile_topup','water']
    provider: str


class SeedUserBiller(StrictModel):
    id: int
    user_id: int
    biller_id: int
    account_number: str
    label: str


class SeedBill(StrictModel):
    id: int
    user_biller_id: int
    period: str
    amount_iqd: int = Field(gt=0)
    due_date: str
    status: Literal['unpaid','paid']


class SeedTransaction(StrictModel):
    id: str
    user_id: int
    type: Literal['transfer','bill_payment']
    payee_ref: str
    amount_iqd: int = Field(gt=0)
    fee_iqd: int = Field(ge=0)
    status: Literal['succeeded','failed']
    created_at: int
    idempotency_key: str


class Seed(StrictModel):
    users: list[SeedUser]
    contacts: list[SeedContact]
    billers: list[SeedBiller]
    user_billers: list[SeedUserBiller]
    bills: list[SeedBill]
    history: list[SeedTransaction]

    @model_validator(mode='after')
    def references(self):
        users = {x.id for x in self.users}
        billers = {x.id for x in self.billers}
        links = {x.id for x in self.user_billers}
        for group in [self.users,self.contacts,self.billers,self.user_billers,self.bills,self.history]:
            if len({x.id for x in group}) != len(group):
                raise ValueError('duplicate IDs')
        if any(x.user_id not in users for x in self.contacts + self.user_billers + self.history):
            raise ValueError('unknown user')
        if any(x.biller_id not in billers for x in self.user_billers) or any(x.user_biller_id not in links for x in self.bills):
            raise ValueError('unknown bill reference')
        return self
