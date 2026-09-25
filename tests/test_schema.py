from sqlalchemy import inspect
from wallet_api.schemas import Payment, Intent, ChatRequest, DraftRequest


def test_tables(engine):
    assert len(inspect(engine).get_table_names()) == 9


def test_round_trips():
    for model in [Payment(user_id=1, amount_iqd=100, payee_id=2), Intent(type='transfer'),
                  ChatRequest(user_id=1, text='مرحبا'), DraftRequest(draft_id='test')]:
        assert type(model).model_validate_json(model.model_dump_json()) == model
