"""Generate the frozen held-out set once. Never overwrites, so hand edits are safe.

    LLM_PROVIDER=groq python -m data.generate_mock_data seed      -> data/heldout_seed.json  (+ .provenance.json)
    LLM_PROVIDER=groq python -m data.generate_mock_data testset   -> data/heldout.jsonl

Then: hand-review, commit (that commit is the freeze), and never tune the system on these files.
"""
import hashlib
import json
import sys
from pathlib import Path
from agent.env import load_env
from .models import Seed
from .synthetic import model_client, make_wallet, make_requests, user_view, check_references  # noqa: F401 (re-export)

HERE = Path(__file__).parent
SEED, TESTSET = HERE / 'heldout_seed.json', HERE / 'heldout.jsonl'
client = model_client  # tests replace this to prove no model is called when files already exist


def write_new(path, text):
    if path.exists(): raise SystemExit(f'{path.name} exists; it may hold hand edits. Delete it yourself to regenerate.')
    path.write_text(text, encoding='utf-8')


def generate_seed():
    if SEED.exists(): raise SystemExit(f'{SEED.name} exists; refusing to regenerate frozen data.')
    seed, blueprint = make_wallet(client())
    write_new(SEED, seed.model_dump_json(indent=2))
    write_new(SEED.with_suffix('.provenance.json'), blueprint.model_dump_json(indent=2))


def generate_testset():
    if TESTSET.exists(): raise SystemExit(f'{TESTSET.name} exists; refusing to regenerate frozen data.')
    seed = Seed.model_validate_json(SEED.read_text(encoding='utf-8'))
    cache = HERE / 'generation'; cache.mkdir(exist_ok=True)
    items = make_requests(client(), user_view(seed), cache, hashlib.sha256(SEED.read_bytes()).hexdigest()[:12])
    if len(items) < 50: raise SystemExit(f'only {len(items)} valid items; the brief needs 50. Cached batches are kept; rerun to resume.')
    check_references(items, seed)
    write_new(TESTSET, ''.join(json.dumps(i.model_dump() | {'expected_final': i.expected_final.model_dump(exclude_none=True)},
                                          ensure_ascii=False) + '\n' for i in items))
    print(f'Wrote {len(items)} requests to {TESTSET.name}. Hand-review them, then commit to freeze.')


if __name__ == '__main__':
    load_env()
    {'seed': generate_seed, 'testset': generate_testset}[sys.argv[1]]()
