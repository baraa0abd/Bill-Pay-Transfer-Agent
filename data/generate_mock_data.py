"""Optional online generator. Committed synthetic seed never depends on an API key."""
import json
from pathlib import Path
import anthropic
from agent.parser import MODEL
from .models import Seed


def generate():
    prompt = ('Generate fictional Iraqi wallet demo data only: exactly 5 users, 20-40 contacts per user, '
              'national electricity, generator, internet, water and three mobile providers, '
              '3-6 months of bill and transaction history. All money integer IQD. '
              'Include ambiguous Ahmed contacts and a low-balance user.')
    # Large output: stream so the request can't hit an HTTP timeout.
    with anthropic.Anthropic().beta.messages.stream(
            model=MODEL, max_tokens=64000, messages=[{'role':'user','content':prompt}], output_format=Seed,
            betas=['server-side-fallback-2026-07-01'], fallbacks='default') as stream:
        msg = stream.get_final_message()
    if msg.stop_reason != 'end_turn' or msg.parsed_output is None:
        raise ValueError(f'Generation incomplete: {msg.stop_reason}')
    seed = msg.parsed_output
    if len(seed.users) != 5 or any(not 20 <= sum(c.user_id == u.id for c in seed.contacts) <= 40 for u in seed.users):
        raise ValueError('Incorrect dataset size')
    Path(__file__).with_name('generated.json').write_text(seed.model_dump_json(indent=2), encoding='utf-8')


if __name__ == '__main__':
    generate()
