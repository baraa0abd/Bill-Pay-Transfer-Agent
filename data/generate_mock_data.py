"""Optional online generator. Committed synthetic seed never depends on an API key."""
import json
import os
from pathlib import Path
import httpx
from .models import Seed


def generate():
    schema = Seed.model_json_schema()
    prompt = ('Generate fictional Iraqi wallet demo data only: exactly 5 users, 20-40 contacts per user, '
              'national electricity, generator, internet, water and three mobile providers, '
              '3-6 months of bill and transaction history. All money integer IQD. '
              'Include ambiguous Ahmed contacts and a low-balance user. Return only JSON matching: ' + json.dumps(schema))
    key = os.environ['LLM_API_KEY']
    provider = os.getenv('LLM_PROVIDER', 'openai')
    model = os.environ['LLM_MODEL']
    if provider == 'anthropic':
        r = httpx.post('https://api.anthropic.com/v1/messages', headers={'x-api-key':key,'anthropic-version':'2023-06-01'},
                       json={'model':model,'max_tokens':16000,'temperature':0,'messages':[{'role':'user','content':prompt}]}, timeout=180)
        r.raise_for_status()
        raw = r.json()['content'][0]['text']
    elif provider == 'openai':
        r = httpx.post('https://api.openai.com/v1/chat/completions', headers={'Authorization':f'Bearer {key}'},
                       json={'model':model,'temperature':0,'messages':[{'role':'user','content':prompt}], 'response_format':{'type':'json_object'}}, timeout=180)
        r.raise_for_status()
        raw = r.json()['choices'][0]['message']['content']
    else:
        raise ValueError('Select openai or anthropic for generation')
    seed = Seed.model_validate_json(raw)
    if len(seed.users) != 5 or any(not 20 <= sum(c.user_id == u.id for c in seed.contacts) <= 40 for u in seed.users):
        raise ValueError('Incorrect dataset size')
    Path(__file__).with_name('generated.json').write_text(seed.model_dump_json(indent=2), encoding='utf-8')


if __name__ == '__main__':
    generate()
