from pathlib import Path
from data.models import Seed
from data.seed import load_seed
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from wallet_api.models import Contact


def test_seed(engine):
    seed = Seed.model_validate_json(Path('data/seed.json').read_text(encoding='utf-8'))
    assert Seed.model_validate_json(seed.model_dump_json()) == seed
    assert len(seed.users) == 5
    assert all(20 <= sum(c.user_id == u.id for c in seed.contacts) <= 40 for u in seed.users)
    names = {c.display_name for c in seed.contacts if c.user_id == 1}
    assert {'أحمد علي','احمد الموصلي','أبو أحمد','حسين','حسن','علي','عليّة','خالو'} <= names
    assert {'electricity_national','generator','mobile_topup','internet'} <= {b.category for b in seed.billers}
    assert any(b.status == 'paid' for b in seed.bills)
    assert load_seed(engine)
    assert not load_seed(engine)
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(Contact)) == 120
