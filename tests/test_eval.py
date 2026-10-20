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
    assert all(i['human_review'] and i['review_status'] for i in items)


def test_evaluation_detects_wrong_payee():
    item={'text':'دز 1000 لخالو','expected_outcome':'EXECUTE_AFTER_CONFIRM','expected_final':{'type':'transfer','payee_id':1,'amount_iqd':1000},'expected_intent_types':['transfer'],'expected_intent_count':1}
    result=run_case(item,RuleBasedParser())
    assert result['unsafe'] and not result['pass']


def test_metrics_use_the_parse_that_drove_the_payment():
    class Once:
        calls = 0
        def parse(self, text):
            self.calls += 1
            assert self.calls == 1, 'Evaluator must not make an independent second parse'
            return RuleBasedParser().parse(text)
    parser = Once()
    item = dict(text='دز 1000 لخالو', expected_outcome='EXECUTE_AFTER_CONFIRM',
                expected_final=dict(type='transfer',payee_id=8,amount_iqd=1000),
                expected_intent_types=['transfer'],expected_intent_count=1)
    result = run_case(item, parser)
    assert result['pass'] and result['type_ok'] and parser.calls == 1


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


def test_model_answers_cached_and_outages_counted(tmp_path, monkeypatch):
    import eval.run_eval as ev
    from agent.hosted_client import ProviderError
    from agent.parser import FallbackParser
    monkeypatch.setattr(ev, 'ROOT', tmp_path)
    class Model:
        model, calls, down = 'fake', 0, False
        def parse(self, text):
            self.calls += 1
            if self.down: raise ProviderError('groq 429: daily tokens')
            return RuleBasedParser().parse(text)
    llm = Model(); cached = ev.CachedModel(llm)
    assert cached.parse('دز 1000 لخالو') == cached.parse('دز 1000 لخالو') and llm.calls == 1  # k runs share one call
    assert ev.CachedModel(llm).parse('دز 1000 لخالو') and llm.calls == 1  # a rerun resumes from disk
    llm.down = True
    with pytest.raises(ProviderError): cached.parse('شكد رصيدي')
    with pytest.raises(ProviderError): cached.parse('سدد المولدة')
    assert llm.calls == 2  # stops calling after the first outage; outages are not cached
    ev.PROVIDER_ERRORS.clear()
    ev.RecordingParser(FallbackParser(cached)).parse('شكد رصيدي')  # rules answered, but the outage is still counted
    assert len(ev.PROVIDER_ERRORS) == 1
