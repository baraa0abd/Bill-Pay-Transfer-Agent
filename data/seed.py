import os
from pathlib import Path
from sqlalchemy import select
from wallet_api.db import Base, make_engine, immediate
from wallet_api.models import User, Contact, Biller, UserBiller, Bill, Transaction
from data.models import Seed


def load_seed(engine, path=None):
    data = Seed.model_validate_json(Path(path or Path(__file__).with_name('seed.json')).read_text(encoding='utf-8'))
    Base.metadata.create_all(engine)
    with immediate(engine) as s:
        if s.scalar(select(User.id).limit(1)) is not None:
            return False
        for model, rows in [(User,data.users),(Biller,data.billers),(Contact,data.contacts),(UserBiller,data.user_billers),(Bill,data.bills),(Transaction,data.history)]:
            s.add_all(model(**x.model_dump()) for x in rows)
            s.flush()
    return True


if __name__ == '__main__':
    # SEED_PATH=data/heldout_seed.json seeds the demo with the LLM-generated wallet.
    print('Seed loaded' if load_seed(make_engine(),os.getenv('SEED_PATH')) else 'Existing database preserved')
