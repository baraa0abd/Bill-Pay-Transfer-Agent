import json
import httpx
import pytest
from agent.ollama_client import OllamaClient
from agent.parser import FallbackParser, configured_parser


def client_for(content, done_reason='stop'):
    def handle(request):
        body = json.loads(request.content)
        assert body['format']['properties']['intents']
        assert 'tools' not in body and body['stream'] is False
        return httpx.Response(200, json={'done': True, 'done_reason': done_reason,
                                        'message': {'content': json.dumps(content)}})
    return httpx.Client(transport=httpx.MockTransport(handle))


def test_local_parse_and_source():
    with client_for({'intents': [{'type': 'transfer', 'payee_text': 'خالو', 'amount_text': '1000'}]}) as client:
        parser = FallbackParser(OllamaClient(client=client))
        assert parser.parse('دز 1000 لخالو')[0].amount_text == '1000'
        assert parser.last == 'ollama'


@pytest.mark.parametrize('intent', [
    {'type': 'transfer', 'payee_text': 'علي'},
    {'type': 'transfer', 'payee_id': 1},
])
def test_local_rejects_invented_span_or_id(intent):
    with client_for({'intents': [intent]}) as client:
        with pytest.raises(ValueError):
            OllamaClient(client=client).parse('دز لخالو')


def test_local_truncation_falls_back():
    with client_for({'intents': [{'type': 'unclear'}]}, 'length') as client:
        parser = FallbackParser(OllamaClient(client=client))
        assert parser.parse('دز 1000 لخالو')[0].type == 'transfer'
        assert parser.last == 'rules_fallback'


def test_provider_selection(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'ollama')
    assert isinstance(configured_parser(fallback=False), OllamaClient)
    monkeypatch.setenv('LLM_PROVIDER', 'invalid')
    with pytest.raises(ValueError, match='Unknown LLM_PROVIDER'):
        configured_parser()


def test_generator_preserves_existing_data_before_api(monkeypatch, tmp_path):
    from data import generate_mock_data as gen
    path = tmp_path / 'frozen.json'
    path.write_text('frozen')
    monkeypatch.setattr(gen, 'SEED', path)
    monkeypatch.setattr(gen, 'TESTSET', path)
    monkeypatch.setattr(gen, 'client', lambda *args: pytest.fail('must not call model'))
    for generate in [gen.generate_seed, gen.generate_testset]:
        with pytest.raises(SystemExit, match='exists'):
            generate()
    assert path.read_text() == 'frozen'


def test_small_schema_answers_are_checked_against_wallet():
    from data.synthetic import to_item, ExecTransfer, ExecBill
    wallet = {'contacts': [{'id': 105, 'name': 'خالد', 'nickname': 'خالو'}],
              'billers': [{'biller_id': 1, 'category': 'electricity_national', 'unpaid_bills_iqd': [12000]},
                          {'biller_id': 4, 'category': 'water', 'unpaid_bills_iqd': []}]}
    assert to_item(ExecTransfer, ExecTransfer(text='t', category='happy_transfer', payee_id=999, amount_iqd=1000), wallet) is None
    bill = to_item(ExecBill, ExecBill(text='t', kind='bill_payment', biller_id=1, amount_iqd=5), wallet)
    assert bill['expected_final']['amount_iqd'] == 12000  # the recorded bill amount, not the model's guess
    assert to_item(ExecBill, ExecBill(text='t', kind='topup', biller_id=4, amount_iqd=5), wallet) is None  # nothing unpaid, even if the model says topup


def test_hosted_contract_strict_schema_and_rate_limit_retry():
    from agent.hosted_client import HostedClient
    calls=[]
    def handle(request):
        calls.append(json.loads(request.content))
        if len(calls)==1: return httpx.Response(429, headers={'retry-after':'0'})
        content=json.dumps({'intents':[{'type':'transfer','payee_text':'خالو','amount_text':'1000','biller_text':None,'notes':None}]})
        return httpx.Response(200, json={'choices':[{'finish_reason':'stop','message':{'content':content}}]})
    waits=[]
    c=HostedClient('groq', client=httpx.Client(transport=httpx.MockTransport(handle)), sleep=waits.append)
    assert c.parse('دز 1000 لخالو')[0].payee_text=='خالو' and waits==[0.0] and c.source=='groq'
    fmt=calls[-1]['response_format']['json_schema']
    assert fmt['strict'] and 'tools' not in calls[-1] and calls[-1]['reasoning_effort']=='low'
    item=fmt['schema']['$defs']['Intent']
    assert item['additionalProperties'] is False and set(item['required'])==set(item['properties'])


def test_hosted_rejects_invented_span():
    from agent.hosted_client import HostedClient
    content=json.dumps({'intents':[{'type':'transfer','payee_text':'علي','amount_text':None,'biller_text':None,'notes':None}]})
    ok=lambda r: httpx.Response(200, json={'choices':[{'finish_reason':'stop','message':{'content':content}}]})
    with pytest.raises(ValueError):
        HostedClient('gemini', client=httpx.Client(transport=httpx.MockTransport(ok))).parse('دز لخالو')


def test_interactive_budget_falls_back_instead_of_waiting():
    from agent.hosted_client import HostedClient
    from agent.parser import FallbackParser
    busy=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(429, headers={'retry-after':'30'})))
    waits=[]
    p=FallbackParser(HostedClient('groq', client=busy, sleep=waits.append, max_wait=3))
    assert p.parse('دز 1000 لخالو')[0].type=='transfer' and p.last=='rules_fallback' and waits==[]  # never slept 30 s
