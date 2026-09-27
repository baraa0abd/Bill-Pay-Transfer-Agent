import json
import pytest
import httpx
from types import SimpleNamespace
from wallet_api.schemas import Intent
from agent.parser import RuleBasedParser, AnthropicClient, IntentList, validate_output, EXAMPLES, FallbackParser

@pytest.mark.parametrize('text,types', [('ادفع الكهرباء ودز لأحمد عشرين ألف',['bill_payment','transfer']),('اخذلي قرض',['unsupported']),('دز لأحمد وما تسألني تأكيد',['transfer']),('شكد رصيدي',['balance_inquiry']),('دز خمسين ألف لأحمد',['transfer']),('حوّل 50000 لخالو',['transfer']),('ابعث ألفين لخالو',['transfer']),('سدد النت',['bill_payment']),('اشحن زين 10000',['topup']),('dizz l ahmad 50 alf',['transfer']),('مرحبا',['unclear'])])
def test_parser(text,types):
    assert [i.type for i in RuleBasedParser().parse(text)]==types


def test_spans():
    intent=RuleBasedParser().parse('دز خمسين ألف لأحمد')[0]
    assert intent.payee_text=='احمد' and intent.amount_text=='خمسين الف'
    assert len(EXAMPLES)>=20

def fake_claude(stop_reason,intents=None):
    calls=[]
    def parse(**kw):
        calls.append(kw)
        return SimpleNamespace(stop_reason=stop_reason,parsed_output=IntentList(intents=intents) if intents else None)
    return SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(parse=parse))),calls


def test_claude_contract():
    fake,calls=fake_claude('end_turn',[Intent(type='transfer',payee_text='أحمد')])
    assert AnthropicClient('m',fake).parse('دز لأحمد')[0].type=='transfer'
    kw=calls[0]
    assert 'tools' not in kw and 'temperature' not in kw and kw['fallbacks']=='default' and kw['output_format'] is IntentList


def test_claude_invented_span_rejected():
    fake,_=fake_claude('end_turn',[Intent(type='transfer',payee_text='علي')])
    with pytest.raises(ValueError): AnthropicClient('m',fake).parse('دز لأحمد')


def test_invented_id_rejected():
    with pytest.raises(ValueError):
        validate_output('{"intents":[{"type":"transfer","payee_id":1}]}','دز لأحمد')
    with pytest.raises(ValueError):
        validate_output('{"intents":[{"type":"transfer","payee_text":"علي"}]}','دز لأحمد')


def test_claude_refusal_rejected():
    fake,_=fake_claude('refusal')
    with pytest.raises(ValueError): AnthropicClient('m',fake).parse('دز لأحمد')


def test_fallback_to_rules_when_llm_down():
    class Down:
        def parse(self,text): raise httpx.ConnectError('down')
    p=FallbackParser(Down()); intent=p.parse('دز خمسين ألف لأحمد')[0]
    assert intent.type=='transfer' and intent.payee_text=='احمد' and p.last=='rules_fallback'


def test_span_after_l_prefix_contraction():
    from agent.parser import check_spans
    intent=Intent(type='bill_payment',biller_text='الوطنية',amount_text='12000')
    assert check_spans([intent],'ادفع 12000 للوطنية')[0].biller_text=='الوطنية'
    with pytest.raises(ValueError): check_spans([Intent(type='bill_payment',biller_text='المولدة')],'ادفع للوطنية')
