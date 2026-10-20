# Disclosure

Everything used to build this project. Update this file whenever something is added.

## AI coding assistants

| Tool | Used for |
|---|---|
| OpenAI Codex (agent) | Wrote the initial codebase, tests, seed data and test set in phases 0–11 (commits authored `Codex`, 2026-09-25). Models recorded in the local Codex session logs (`~/.codex/sessions`): 2026-09-25 `gpt-5.6-sol` and `gpt-6-astra`, with `codex-auto-review` as the reviewer; 2026-09-27 the same three. |
| Claude Code (Claude Opus 5.5) | Gap analysis against the topic brief, this file, `FAILURE_MODES.md`, `ARCHITECTURE.md`, design brief, parser-outage test, Claude SDK parser, rule fallback, free Groq/Gemini client, latency budget, provider-agnostic synthetic-data pipeline, held-out generation and label checks, review page and spreadsheet, eval mode and freeze hashing, parser badge, recovered-payment receipt, evaluation answer cache and typed provider errors, code review fixes (unmounted the wallet API, whole-word biller keywords, stale top-up drafts), running the generation and evaluations |

Follow-up (2026-09-27): Codex added the local Ollama adapter, compact wallet-blueprint generation, per-case AI review notes, report provenance fixes and a fresh-database local demo launcher. These are AI edits, not human or native-speaker review.

## Models at runtime

| Component | Model | Status |
|---|---|---|
| Intent parser (default) | Groq `openai/gpt-oss-120b`, free tier, strict JSON schema, low reasoning effort, 3 s budget in the app; rule parser as fallback | Run live since 2026-10-17; dev set 68/68 alone and as full system (`eval/report-groq*.md`, raw answers in `eval/llm-cache/`) |
| Local intent parser | Ollama `qwen3.5:4b`, schema-constrained JSON and validated text spans | Offline option; results in `eval/report-ollama*.md` and `eval/report-heldout-v1*` |
| Paid option | Anthropic `claude-opus-5` via the `anthropic` SDK (`LLM_PROVIDER=anthropic`) | Not run live (no free tier); contract-tested with a fake client |
| Held-out data generator | Groq `openai/gpt-oss-120b` (fresh set, 2026-10-17); Ollama `qwen3.5:4b` for v1 | Wallet blueprint + deterministic expansion; requests per outcome; raw batches kept in `data/generation/` |
| Gemini option | Gemini `gemini-3.8-flash` via the same OpenAI-compatible client (`LLM_PROVIDER=gemini`) | Contract-tested; not run live |
| Tried and dropped | Groq `qwen/qwen3.8-27b` as a consensus second model | Did not fix the case it targeted, misread «ادفع لريم», doubled free-tier use |
| Speech-to-text (stretch) | OpenAI `whisper-1` via `voice/asr.py` | **Not tested with real audio** |
| Text-to-speech | Interface only (`voice/tts.py`) | Not enabled |

The model only extracts text spans. Contact/biller resolution, amounts, balance checks, confirmation and execution are deterministic code.

## Data

All data is synthetic. No real customer records, phone numbers, accounts or transactions.

| File | Source |
|---|---|
| `data/seed.json` (5 users, 24 contacts each, 7 billers, 4 months of bills) | Authored by Codex locally, **not** generated through a live LLM API. Kept as the development fixture because tests and the dev set reference its IDs; the LLM-generated wallet is the held-out one. |
| `data/testset.jsonl` (68 requests) | Curated by Codex. **Development set, not held out**: the rule parser was developed against it. Not yet reviewed by a native speaker. |
| `data/heldout_v1_seed.json`, `data/heldout_v1.jsonl` (archived; used to find fixes, so no longer blind) | Local Ollama `qwen3.5:4b` through `data/generate_mock_data.py`. Model-authored wallet fields are preserved in `heldout_seed.provenance.json`; identifiers and historical rows are deterministic expansion. Post-generation fixes by Claude Code (not human): the model's 32 contacts were deduplicated to the first 24 distinct names; invoice amount 8,500 was rounded to 8,000; the garbled biller name «زain موبايل» was corrected to «زين موبايل». No human editing is claimed yet. |
| `data/heldout_seed.json`, `data/heldout.jsonl` (fresh held-out) | Generated 2026-10-17 with Groq `openai/gpt-oss-120b` via `data/synthetic.py`: 110 requests, all passed the wallet checks. AI (Claude Code) corrected 11 objectively wrong labels and flagged 5, each marked per item. **Native-speaker review pending; not yet frozen or scored.** |
| `data/schema.json` | JSON Schema for the mock wallet dataset |

## Libraries

Runtime: Anthropic Python SDK, FastAPI, Uvicorn, SQLAlchemy, Pydantic, HTTPX, RapidFuzz, python-multipart.
Test: pytest, pytest-asyncio, jsonschema. Tools (`pip install -e .[tools]`): openpyxl (review spreadsheet), reportlab, arabic-reshaper, python-bidi, pypdfium2 (design-brief PDF).
Exact versions: `requirements-lock.txt`.

## External services

None required (the rule parser works offline). Used: Groq free tier (parser, data generation). Optional: Gemini, Anthropic, OpenAI transcription (voice). Only synthetic data is ever sent, and only when the corresponding key is set in the untracked `.env`.
