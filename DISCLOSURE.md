# Disclosure

Everything used to build this project. Update this file whenever something is added.

## AI coding assistants

| Tool | Used for |
|---|---|
| OpenAI Codex (agent) | Wrote the initial codebase, tests, seed data and test set in phases 0–11 (commits authored `Codex`, 2026-09-25). Model version: **TODO — fill in from Codex settings** |
| Claude Code (Claude Opus 5.5) | Gap analysis against the topic brief, this file, `FAILURE_MODES.md`, parser-outage test |

## Models at runtime

| Component | Model | Status |
|---|---|---|
| Intent parser | `LLM_PROVIDER=rule` (deterministic, no model) is the current default. `anthropic` / `openai` adapters exist in `agent/parser.py`. | Live LLM parsing **not yet run**; contract-tested with mocked HTTP only |
| Speech-to-text (stretch) | OpenAI `whisper-1` via `voice/asr.py` | **Not tested with real audio** |
| Text-to-speech | Interface only (`voice/tts.py`) | Not enabled |

The model only extracts text spans. Contact/biller resolution, amounts, balance checks, confirmation and execution are deterministic code.

## Data

All data is synthetic. No real customer records, phone numbers, accounts or transactions.

| File | Source |
|---|---|
| `data/seed.json` (5 users, 24 contacts each, 7 billers, 4 months of bills) | Authored by Codex locally, **not** generated through a live LLM API. `data/generate_mock_data.py` can regenerate it from a provider; not yet run. |
| `data/testset.jsonl` (68 requests) | Curated by Codex. **Not held out**: the rule parser was developed against it. Not yet reviewed by a native speaker. |
| `data/schema.json` | JSON Schema for the mock wallet dataset |

## Libraries

Runtime: FastAPI, Uvicorn, SQLAlchemy, Pydantic, HTTPX, RapidFuzz, python-multipart.
Test: pytest, pytest-asyncio, jsonschema.
Exact versions: `requirements-lock.txt`.

## External services

None required. Optional: Anthropic or OpenAI API (parser), OpenAI transcription API (voice). Nothing is sent unless the corresponding key is set.
