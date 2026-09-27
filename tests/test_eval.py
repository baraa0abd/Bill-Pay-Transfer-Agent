import pytest
import json
from pathlib import Path
from collections import Counter
from agent.parser import RuleBasedParser
from eval.run_eval import run_case


def test_set_coverage():
    items=[json.loads(x) for x in Path('data/testset.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(items)>=60 and len({i['id'] for i in items})==len(items)
    counts=Counter(i['category'] for i in items)
    assert sum(counts[x] for x in ['ambiguous_contact','ambiguous_biller','ambiguous_amount'])>=8
    assert counts['multi_intent']>=5
    assert sum(counts[x] for x in ['malformed','typo','arabizi'])>=5
    assert all(i['human_review'].startswith('TODO') for i in items)


def test_evaluation_detects_wrong_payee():
    item={'text':'دز 1000 لخالو','expected_outcome':'EXECUTE_AFTER_CONFIRM','expected_final':{'type':'transfer','payee_id':1,'amount_iqd':1000},'expected_intent_types':['transfer'],'expected_intent_count':1}
    result=run_case(item,RuleBasedParser())
    assert result['unsafe'] and not result['pass']


def test_generated_labels_are_checked():
    from pathlib import Path
    from pydantic import ValidationError
    from data.models import Seed, TestItem
    from data.generate_mock_data import check_references
    seed=Seed.model_validate_json(Path('data/seed.json').read_text(encoding='utf-8'))
    ok=dict(id='h1',text='دز 50000 لخالو',category='happy_transfer',expected_outcome='EXECUTE_AFTER_CONFIRM',
            expected_intent_count=1,expected_intent_types=['transfer'],expected_final={'type':'transfer','payee_id':8,'amount_iqd':50000})
    check_references([TestItem(**ok)],seed)
    with pytest.raises(ValueError): check_references([TestItem(**ok|{'expected_final':{'type':'transfer','payee_id':9999,'amount_iqd':50000}})],seed)
    with pytest.raises(ValidationError): TestItem(**ok|{'expected_outcome':'ASK'})  # ASK without a slot
    with pytest.raises(ValidationError): TestItem(**ok|{'expected_outcome':'REFUSE'})  # REFUSE without a code
