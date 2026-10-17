import os
os.environ["LLM_PROVIDER"] = "rule"  # tests never call a real model, whatever .env says
import pytest
from wallet_api.db import Base, make_engine
import wallet_api.models


@pytest.fixture
def engine(tmp_path):
    engine = make_engine('sqlite:///' + str(tmp_path / 'test.db'))
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

