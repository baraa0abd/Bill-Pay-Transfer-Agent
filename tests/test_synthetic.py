from data.synthetic import make_wallet, make_requests, user_view, check_references, WalletBlueprint


class FakeModel:
    """Answers the wallet prompt with a fixed blueprint; request batches get one good item, plus a wrong-ID item for executes."""
    def generate(self, prompt, schema, max_tokens=0):
        if schema is WalletBlueprint:
            names = ['أحمد علي', 'أحمد كاظم', 'حسن جبار', 'حسين ناصر'] + [f'زيد رقم{i}' for i in range(28)]
            return WalletBlueprint(users=[{'name': f'مستخدم{i}', 'balance_iqd': 200000} for i in range(5)],
                                   contacts=[{'name': n, 'nickname': 'خالو' if i == 4 else None} for i, n in enumerate(names)],
                                   biller_names=['الكهرباء الوطنية', 'مولدة الحي', 'انترنت', 'ماء', 'زين', 'آسياسيل', 'كورك'],
                                   bill_amounts=[25000, 39500, 30000, 10000, 5000, 5000, 5000])
        item = schema.model_fields['items'].annotation.__args__[0].__name__
        good = {'ExecTransfer': {'text': 'دز 5000 لخالو', 'category': 'happy_transfer', 'payee_id': 105, 'amount_iqd': 5000},
                'ExecBill': {'text': 'ادفع الوطنية', 'kind': 'bill_payment', 'biller_id': 1, 'amount_iqd': 1},
                'Ask': {'text': 'دز لأحمد 5000', 'category': 'ambiguous_contact', 'slot': 'amount', 'intent': 'topup'},
                'Refuse': {'text': 'اريد قرض', 'category': 'unsupported', 'refuse_code': 'UNCLEAR', 'intent': 'unclear'},
                'Split': {'text': 'دز لخالو وادفع الماء', 'intents': ['transfer', 'bill_payment']}}[item]
        # Real clients validate the batch schema, so the realistic bad answer is an ID that is not in the wallet.
        bad = [good | ({'payee_id': 999} if item == 'ExecTransfer' else {'biller_id': 999})] if item.startswith('Exec') else []
        return schema(items=[good] + bad)


def test_pipeline_builds_wallet_and_checked_labels(tmp_path):
    seed, _ = make_wallet(FakeModel())
    assert len(seed.users) == 5 and {b.provider for b in seed.billers} >= {'zain', 'asiacell', 'korek'}
    assert {b.amount_iqd for b in seed.bills if b.user_biller_id == 102} == {40000}  # 39500 rounded to whole thousands
    wallet = user_view(seed)
    items = make_requests(FakeModel(), wallet, tmp_path, 'fp')
    check_references(items, seed)
    assert len(items) == 11  # one good item per batch; the wrong-ID ones are dropped
    bill = next(i for i in items if i.category == 'happy_bill')
    assert bill.expected_final.amount_iqd == 25000  # the recorded bill amount, not the model's 1
    asks = [i for i in items if i.expected_outcome == 'ASK']
    assert [(a.expected_ask_slot, a.expected_intent_types) for a in asks[:2]] == [('payee', ['transfer']), ('biller', ['bill_payment'])]  # forced labels win
    assert len(list(tmp_path.glob('fp-*.json'))) == 11  # cached, so a rerun resumes
