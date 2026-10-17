# Disclosure

Everything used to build this project. Update this file whenever something is added.

## AI coding assistants

| Tool | Used for |
|---|---|
| OpenAI Codex (agent) | Wrote the initial codebase, tests, seed data and test set in phases 0–11 (commits authored `Codex`, 2026-09-25). Models recorded in the local Codex session logs (`~/.codex/sessions`): 2026-09-25 `gpt-5.6-sol` and `gpt-6-astra`, with `codex-auto-review` as the reviewer; 2026-09-27 the same three. |
| Claude Code (Claude Opus 5.5) | Gap analysis against the topic brief, this file, `FAILURE_MODES.md`, parser-outage test, Claude SDK parser and generator, rule fallback, OpenAI parser removal, held-out generator and eval mode, parser badge, recovered-payment receipt, running the local generation and evaluation |

Follow-up (2026-09-27): Codex added the local Ollama adapter, compact wallet-blueprint generation, per-case AI review notes, report provenance fixes and a fresh-database local demo launcher. These are AI edits, not human or native-speaker review.

## Models at runtime

| Component | Model | Status |
|---|---|---|
| Local intent parser | Ollama `qwen3.5:4b`, schema-constrained JSON and validated text spans | Verification in progress; see README and eval reports |
| Intent parser | Anthropic `claude-opus-5` via the `anthropic` Python SDK (`LLM_PROVIDER=anthropic`), rule parser as fallback. Offline default is the rule parser. | Live LLM parsing **not yet run**; contract-tested with a fake client only |
| Held-out data generator | Ollama `qwen3.5:4b` when LLM_PROVIDER=ollama; Anthropic remains optional | Local blueprint plus deterministic ledger expansion; request batches use the same local model. See generated artifacts and reports for completed runs. |
| Free hosted parser option | Groq `openai/gpt-oss-120b` or Gemini `gemini-3.8-flash` via the OpenAI-compatible API (`agent/hosted_client.py`, `LLM_PROVIDER=groq|gemini`, override with `LLM_MODEL`) | Added 2026-10-17; contract-tested with a mocked API, not yet run live |
| Speech-to-text (stretch) | OpenAI `whisper-1` via `voice/asr.py` | **Not tested with real audio** |
| Text-to-speech | Interface only (`voice/tts.py`) | Not enabled |

The model only extracts text spans. Contact/biller resolution, amounts, balance checks, confirmation and execution are deterministic code.

## Data

All data is synthetic. No real customer records, phone numbers, accounts or transactions.

| File | Source |
|---|---|
| `data/seed.json` (5 users, 24 contacts each, 7 billers, 4 months of bills) | Authored by Codex locally, **not** generated through a live LLM API. Kept as the development fixture because tests and the dev set reference its IDs; the LLM-generated wallet is the held-out one. |
| `data/testset.jsonl` (68 requests) | Curated by Codex. **Development set, not held out**: the rule parser was developed against it. Not yet reviewed by a native speaker. |
| `data/heldout_seed.json`, `data/heldout.jsonl` | Target provider: local Ollama `qwen3.5:4b` through `data/generate_mock_data.py`. Model-authored wallet fields are preserved in `heldout_seed.provenance.json`; identifiers and historical rows are deterministic expansion. Post-generation fixes by Claude Code (not human): the model's 32 contacts were deduplicated to the first 24 distinct names; invoice amount 8,500 was rounded to 8,000; the garbled biller name «زain موبايل» was corrected to «زين موبايل». No human editing is claimed yet. |
| `data/schema.json` | JSON Schema for the mock wallet dataset |

## Libraries

Runtime: Anthropic Python SDK, FastAPI, Uvicorn, SQLAlchemy, Pydantic, HTTPX, RapidFuzz, python-multipart.
Test: pytest, pytest-asyncio, jsonschema.
Exact versions: `requirements-lock.txt`.

## External services

None required. Optional: Anthropic API (parser, data generation), OpenAI transcription API (voice only). Nothing is sent unless the corresponding key is set.
