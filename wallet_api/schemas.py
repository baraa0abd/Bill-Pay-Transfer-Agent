from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Payment(StrictModel):
    user_id: StrictInt
    amount_iqd: StrictInt = Field(gt=0)
    payee_id: StrictInt | None = None
    bill_id: StrictInt | None = None


class Intent(StrictModel):
    type: Literal['transfer', 'bill_payment', 'topup', 'balance_inquiry', 'history_inquiry', 'cancel', 'unsupported', 'unclear']
    payee_text: str | None = None
    biller_text: str | None = None
    amount_text: str | None = None
    notes: str | None = None


class ChatRequest(StrictModel):
    user_id: StrictInt
    conversation_id: str | None = None
    text: str = Field(max_length=4000)


class DraftRequest(StrictModel):
    draft_id: str

