"""Exercise the four demo flows over HTTP with a fresh wallet and no parser fallback."""
import json
import os
import tempfile
import time
from pathlib import Path
from fastapi.testclient import TestClient
from app import create_app
from agent.parser import configured_parser
from data.seed import load_seed
from wallet_api.db import make_engine


def rehearse():
    root=Path(__file__).resolve().parents[1]
    seed=root/os.getenv('SEED_PATH','data/heldout_seed.json')
    directory=root/'.test-tmp'
    directory.mkdir(exist_ok=True)
    steps=[]
    start=time.monotonic()
    with tempfile.TemporaryDirectory(dir=directory) as temp:
        engine=make_engine('sqlite:///'+str(Path(temp)/'demo.db'))
        try:
            load_seed(engine,seed)
            parser=configured_parser(fallback=False)
            with TestClient(create_app(engine,parser=parser,demo_mode=True),headers={'X-User-ID':'1'}) as client:
                def balance(): return client.get('/account').json()['balance']['balance_iqd']
                def chat(text,cid=None):
                    return client.post('/chat',json=dict(user_id=1,text=text,conversation_id=cid)).json()
                before=balance()
                bill=chat('ادفع الكهرباء')
                assert bill.get('ask_slot')=='biller',bill
                bill=chat('1',bill['conversation_id'])
                assert bill.get('card'),bill
                card=bill['card']
                assert balance()==before
                result=client.post('/confirm',json={'draft_id':card['draft_id']}).json()['result']
                assert result['status']=='succeeded',result
                assert balance()==before-result['amount_iqd']-result['fee_iqd']
                steps.append('Electricity: asked which supplier; no debit before confirmation; confirmed exactly one payment.')
                before=balance()
                transfer=chat('دز خمسين ألف لأحمد')
                assert transfer.get('ask_slot')=='payee',transfer
                transfer=chat('1',transfer['conversation_id'])
                assert transfer.get('card'),transfer
                result=client.post('/cancel',json={'draft_id':transfer['card']['draft_id']}).json()['result']
                assert result['code']=='CANCELLED' and balance()==before
                steps.append('Ahmed: asked which contact; cancellation left balance unchanged.')
                refused=chat('دز نص مليون لخالو')
                assert refused.get('code')=='INSUFFICIENT_FUNDS' and not refused.get('card'),refused
                assert balance()==before
                steps.append('Insufficient funds: no review card and no debit.')
                transfer=chat('دز ألف لخالو')
                assert transfer.get('card'),transfer
                key=transfer['card']['draft_id']
                result=client.post('/confirm',json={'draft_id':key},headers={'X-Fault':'DROP_RESPONSE_AFTER_COMMIT'}).json()['result']
                assert result['status']=='succeeded' and result.get('recovered'),result
                replay=client.post('/confirm',json={'draft_id':key}).json()['result']
                assert result['id']==replay['id'] and balance()==before-1250
                steps.append('Lost response: recovered original receipt; repeat confirmation caused no second debit.')
        finally:
            engine.dispose()
    elapsed=time.monotonic()-start
    report={'provider':os.getenv('LLM_PROVIDER','rule'),'model':getattr(parser,'model',None),
            'seed':str(seed.relative_to(root)),'seconds':round(elapsed,2),'steps':steps,
            'scope':'Automated HTTP rehearsal, not a timed human presentation or browser usability study.'}
    (root/'eval/demo-rehearsal.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)


if __name__=='__main__': rehearse()
