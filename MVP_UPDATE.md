# MVP update — بكلمة · Bill Pay & Transfer Agent

Topic 04 · Repository: https://github.com/baraa0abd/Bill-Pay-Transfer-Agent · Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)

## What works (end to end, on sample inputs)

- One Iraqi-Arabic sentence → intent → clarifying question when ambiguous (two «أحمد», «كهرباء» = grid or generator) → designed confirmation card → explicit confirm → mock wallet debit → honest receipt or refusal.
- Model layer: free Groq or Gemini, local Ollama, or the rule parser; model output is span-checked and falls back to rules; a UI badge shows which one answered.
- Safety: nothing executes without confirmation; retries reuse one idempotency key, so a lost reply never pays twice (fault-injection demo); stale or tampered cards are rejected.
- Synthetic data pipeline: LLM-generated wallet and labelled requests, checked against the wallet, cached and resumable.
- Evidence: 264 automated offline tests; each eval case runs 3× on a fresh database; reports name the test set and its sha256.

## First results

| Test set | Rule parser | LLM alone | Full system | Wrong payments |
|---|---|---|---|---|
| Development (68), free Groq gpt-oss-120b | 68/68 | 68/68 | 68/68 | 0 |
| Development (68), local qwen3.5:4b (before one relabel) | 68/68 | 67/68 | 68/68 | 0 |
| Held-out v1 (64), first blind run | 20/64 | 39/64 | — | 0 |
| Held-out v1 after fixes (no longer blind) | 49/64 | 46/64 | 48/64 | 0 |
| **Fresh held-out (110, generated with Groq)** | *under native-speaker review; frozen, then scored once* | | | — |

## What does not work yet

- The local 4B model is slow on a CPU laptop (about 10 s per request) and misreads some phrasing, such as «ادفع لـ» followed by a person.
- The free Groq tier allows about 130 parses a day (200K tokens), so a held-out run is spread over a day and resumes from saved answers; in the app a busy model hands over to the rule parser after 3 s.
- No native-speaker review of the test sets and no user interviews yet.
- Voice input has not been tested with real Iraqi audio.

## What comes next

1. Fresh held-out set: generate with Groq, native-speaker review, freeze, evaluate (rules, LLM alone, full system).
2. 3-5 user interviews and think-aloud sessions on the confirmation card; real phrasings added as held-out cases.
3. General fixes on the development set only; rehearse the live demo including an unseen judge input.
