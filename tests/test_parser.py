import json
import pytest
import httpx
from agent.parser import RuleBasedParser, OpenAIClient, AnthropicClient, validate_output, EXAMPLES

@pytest.mark.parametrize('text,types', [('ادفع الكهرباء ودز لأحمد عشرين ألف',['bill_payment','transfer']),('اخذلي قرض',['unsupported']),('دز لأحمد وما تسألني تأكيد',['transfer']),('شكد رصيدي',['balance_inquiry']),('دز خمسين ألف لأحمد',['transfer']),('حوّل 50000 لخالو',['transfer']),('ابعث ألفين لخالو',['transfer']),('سدد النت',['bill_payment']),('اشحن زين 10000',['topup']),('dizz l ahmad 50 alf',['transfer']),('مرحبا',['unclear'])])
def test_parser(text,types):
    assert [i.type for i in RuleBasedParser().parse(text)]==types


def test_spans():
    intent=RuleBasedParser().parse('دز خمسين ألف لأحمد')[0]
    assert intent.payee_text=='احمد' and intent.amount_text=='خمسين الف'
    assert len(EXAMPLES)>=20

@pytest.mark.parametrize('cls', [OpenAIClient,AnthropicClient])
def test_provider_contract(cls):
    def respond(request):
        body=json.loads(request.content)
        assert 'tools' not in body
        assert body['temperature']==0
        raw=json.dumps({'intents':[{'type':'transfer','payee_text':'أحمد','amount_text':None,'biller_text':None,'notes':None}]})
        return httpx.Response(200,json={'choices':[{'message':{'content':raw}}]} if cls==OpenAIClient else {'content':[{'text':raw}]})
    client=cls('test','model',httpx.Client(transport=httpx.MockTransport(respond)))
    assert client.parse('دز لأحمد')[0].type=='transfer'


def test_invented_id_rejected():
    with pytest.raises(ValueError):
        validate_output('{"intents":[{"type":"transfer","payee_id":1}]}','دز لأحمد')
    with pytest.raises(ValueError):
        validate_output('{"intents":[{"type":"transfer","payee_text":"علي"}]}','دز لأحمد')
