# بكلمة — Bill Pay & Transfer Agent

A local, mock-wallet hackathon app for Iraqi Arabic typed requests, with an optional hosted parser and voice input. **No real money, bank credentials, or real payment integration.**

**For judges:** [Disclosure](DISCLOSURE.md) · [Failure modes](FAILURE_MODES.md) · [Evaluation report](eval/report.md)

## Run

Python 3.11+ is required. From the repository root:

```sh
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
make seed
make test
make eval
make run
```

Open http://localhost:8000. On Windows without GNU Make, use `./make.ps1 seed`, `./make.ps1 test`, `./make.ps1 eval`, and `./make.ps1 run`. These invoke the same Python modules. This workspace includes a project-local virtual environment; Python and GNU Make were absent from PATH during implementation, so all phase gates used `make.ps1`.

Seeding preserves an existing database. To start a separate clean demo, set `DATABASE_URL=sqlite:///fresh-demo.db`, then seed and run. Do not delete a database containing demo transactions you want to retain. `.env.example` documents settings; export them in your shell (the app does not implicitly load `.env`).

PowerShell demo faults:

```powershell
$env:DEMO_MODE='true'
.\make.ps1 run
```

The sidebar lets you simulate a lost response after commit, a crash before commit, delay, and a provider outage. Fault headers are ignored unless demo mode is enabled. This is a localhost development server; do not expose it publicly.

## Architecture

```text
RTL browser / typed text       audio -> ASR -> visible transcript
          |                                  |
          +---------- /chat -----------------+
                         |
          parser (text spans only, NO wallet tools)
                         |
     normalize -> resolve contacts/billers -> parse integer amounts
                         |
          persisted conversation + one-question clarification
                         |
          balance / daily-limit precheck -> immutable draft
                         |
          dedicated review card (expires in 120 seconds)
                         |
         button / exact typed token -> confirm handler
                         |
         owner + state + expiry + payload-hash verification
                         |
          WalletClient, Idempotency-Key = draft UUID
                         |
    mock HTTP wallet -> SQLite BEGIN IMMEDIATE -> ledger / debit
                         |
            receipt OR refusal OR unknown + status polling
```

`wallet_api` owns the ledger. `agent` owns parsing, dialogue, drafts and confirmation. `app.py` composes them using an in-process HTTP transport; the wallet service can also be inspected under `/wallet`. Tests use temporary, file-backed SQLite databases, not shared in-memory databases. The seed contains 5 users, 24 contacts each, 7 providers, and four months of historical bills. Seed history is illustrative and does not reconstruct the opening balance.

## Safety invariant

The parser never receives execution tools. It outputs a validated list of span-only intents. Any model-invented identifier or span is rejected. The sole agent call to `WalletClient.execute` is in `Confirmer.confirm`; a static AST test and runtime flow tests enforce that boundary.

The handler verifies ownership, pending state, expiration and SHA-256 of canonical JSON, then records authorization atomically. Concurrent calls and recovery of an already-authorized request reuse the same UUID. A confirmed draft may be resumed after expiry; it is the already-approved operation, never a new payment. Unconfirmed expired drafts cannot execute. A missing final response is **not** proof of failure. Polling looks up the original key. Explicitly retrying the same confirmed draft safely recovers a crash between authorization and wallet execution.

Amounts and balances use strict integer IQD throughout. Provider similarity scores and retry delays are not money. The mock fee is 250 IQD per debit; daily limits include fees and use UTC calendar days. Both balances and limits are rechecked in the atomic wallet transaction. Contacts represent external recipients; no second internal account is credited.

Mock identity is selected with `X-User-ID`; `/chat` also verifies that its user_id matches. This is explicitly not production authentication. Raw wallet endpoints are a separate mock-service boundary, not LLM tools. Real authorization, CSRF/session policy, distributed services, schema migrations, production observability and deployment hardening are outside this demo.

## Retry safety

See [the automated idempotency proof](eval/idempotency_proof.md). A `(user_id, key)` uniqueness constraint, request fingerprint, 30-second lease and durable result cache protect retries. Debit, bill status and ledger insertion commit together. Successful ledger records retain a permanent original receipt/fingerprint tombstone even after the 24-hour response cache is cleaned. Reusing an old successful key never causes a new debit. Failed results also replay during the cache window. `wallet_api.idempotency.cleanup(engine)` can be called by a maintenance job.

The included fault tests cover 50 concurrent requests, changed payload conflicts, rollback before commit, lost responses after commit, expired leases, cache cleanup, and two concurrent confirmations. Under real process death an unexpired lease can return in-progress until it expires; the UI remains in status verification rather than claiming failure.

## Confirmation design

The card is distinct from chat text and shows the full destination, masked phone/account, bill period, digits and Arabic words, fee, balance before/after, deadline, and two explicit buttons. A recent matching successful payment adds a warning without silently blocking an intentional repeat. All inserted chat/provider text uses DOM `textContent`, not HTML interpolation. Old card controls are disabled after an action; server validation remains authoritative.

Only normalized exact tokens `أكد`, `اكد`, `تأكيد`, `نعم أكد` confirm. “اوك”, “زين”, “نعم” and longer sentences do not. Every queued payment has its own draft and confirmation. Cancellation applies to unexecuted work and cannot undo an authorized debit. Optional mock PIN is not enabled.

## Dialect assumptions to verify

- `ميت ألف` / `مية ألف` mean 100,000 IQD; `نص مليون`, `ربع مليون`, `مليون ونص`, `مليونين`, `ألفين` are explicitly supported.
- Bare values below 1,000 without a unit are ambiguous. Explicit `50 دينار` is accepted as 50 IQD. Larger numeric values such as `50000` mean IQD.
- Unknown money slang (`ورقة`, `دفتر`, or malformed separators/decimals) prompts for clarification. No exchange-rate or slang meaning is invented.
- Electricity includes national grid and neighborhood generator unless specified. Fuzzy matches require score >=90 and a >=15 point lead; candidate floor is 80. Non-exact contact matches always require a choice, even above the score threshold. Similar short names can require a choice even on exact spelling.
- Known Arabizi forms `dizz l ahmad 50 alf` and `dizz l khalo 50 alf` are supported; other spellings fail conservatively.
- Top-ups create an unpaid mock invoice for the chosen provider/account and amount. Existing invoices must be paid for their exact recorded amount. Multiple unpaid periods require a period choice.
- A native Iraqi speaker must review wording, names, transliteration, amount words and the test set. No human review is claimed.

## Optional online parsing and data generation

Default `LLM_PROVIDER=rule` needs no credentials and never contacts an LLM. For live parsing set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY` (`LLM_MODEL` defaults to `claude-opus-5`). The parser uses the official `anthropic` SDK with a Pydantic output schema, 24 examples, low effort and server-side refusal fallbacks. If the provider is down, refuses, or returns a span not in the user's text, the app falls back to the rule parser; `make eval` measures the LLM alone, without that fallback.

Claude is the only parser model; OpenAI was removed to keep one LLM path. See [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs). The adapter is contract-tested offline with a fake client; no live accuracy claim is made until `eval/report-anthropic.md` exists.

`python -m data.generate_mock_data` optionally requests synthetic data from the configured provider, validates it against Pydantic, and writes ignored `data/generated.json`. The committed seed was explicitly authored locally, not generated by a live API. `data/schema.json` is the JSON Schema for this dataset. Native-speaker review remains required before replacing the committed seed with generated data.

## Tests and evaluation

`make test` / `./make.ps1 test` runs all tests offline. `make eval` runs 68 curated requests three times each with a fresh seeded database and writes [eval/report.md](eval/report.md) and machine-readable [eval/results.json](eval/results.json). Each item only passes if all three runs pass. The report includes unsafe execution, success, clarification, over-asking, split and parser metrics; all failures include expected and actual outcomes.

Only `EXECUTE_AFTER_CONFIRM` evaluation cases are auto-confirmed. ASK and SPLIT cases are not executed; full sequential execution is covered separately by confirmation and HTTP tests. Payee ID, provider ID, type and amount are all checked against fixtures. A negative-control test proves the evaluator detects an intentionally wrong payee expectation.

The JSONL cases were curated by the implementation agent. `hand_edited: true` means individually edited fixtures, **not human/native-speaker approval**; every item has `human_review: TODO`. Optional live evaluation writes a separate provider report. The >=95% LLM-parser target and live-provider unsafe-execution rate are unverified without credentials. Offline success is not evidence of open-ended language accuracy.

## Implementation phase notes

All phase commits followed a passing offline suite using the Windows Make equivalent. Some requested acceptance checks depend on later phases: phase 2 double-confirm coverage landed in phase 7; phase 5 full-dataset evaluation landed in phase 10; phase 6 sequential confirmed execution landed in phase 7. Live-LLM generation/evaluation and human review could not be performed offline and are explicitly pending.

## Phase gate record

| Phase | Green offline tests | Additional verification / remaining dependency |
|---|---:|---|
| 0 — setup/schema | 2 | All nine tables and request schema round trips |
| 1 — wallet | 10 | Integer validation, exact debit, insufficient funds, paid bills |
| 2 — idempotency/faults | 19 | 50 concurrent requests; double-confirm test deferred to phase 7 |
| 3 — seed | 20 | Planted cases and 120 contacts; live generation not run |
| 4 — normalization/resolvers | 138 | 118 normalization, amount and resolver cases |
| 5 — parser | 153 | Provider HTTP contracts mocked; live accuracy not measured |
| 6 — dialogue | 161 | Restart, cancellation, edits, queue; execution deferred to phase 7 |
| 7 — confirmation | 175 | Double tap, invalid drafts, two confirmations, AST boundary |
| 8 — outcome messages | 203 | Ledger-truth and unresolved-then-reconciled outcomes |
| 9 — UI/HTTP | 215 | Ten HTTP flows plus live browser card/cancel check |
| 10 — evaluation | 217 | 68 cases × 3 runs; see generated report |

## Voice stretch

Set `ASR_API_KEY` (and optionally `ASR_MODEL=whisper-1`) to enable the microphone button. Click to record and click again to stop; recording stops after 30 seconds. The server accepts WAV/WebM up to 8 MiB. The hosted adapter follows the [OpenAI transcription API](https://developers.openai.com/api/docs/guides/speech-to-text). It sends audio only when the user records/submits it.

Every response displays the transcript. Unknown confidence, confidence below 90/100, or any uncertain name/amount tokens force the user to type the corrected request. Hosted Whisper JSON does not supply a calibrated confidence, so the default adapter deliberately requests text review. Injected ASR providers can supply confidence/uncertain tokens, but this is not a guarantee of correctness. Even a high-confidence spoken “أكد” cannot execute; only a subsequent button click or exact typed confirmation can.

Real audio was not supplied, so live transcription and microphone hardware were not tested. `MockASR` covers low confidence, misheard names, corrected text, and attempted spoken confirmation. Optional TTS is an interface only and is not enabled.

To evaluate your own recordings, put WAV/WebM files in `data/audio/` and add `manifest.jsonl` entries such as `{"file":"request.wav","testset_id":"iq-001"}`. With `ASR_API_KEY` set, `make eval` runs each through `/voice` three times and adds matched voice/text success and unsafe-execution metrics. Missing credentials/annotations are explicitly reported, never counted as a passing audio evaluation. Do not commit personal audio or credentials.

Phase 11 gate: 224 offline tests pass, including 7 voice tests. Text evaluation remains 68/68 items across three runs with zero unsafe executions. No real audio or live model evaluation was performed.


Final regression checks additionally cover concurrent different-key debits (no overdraw), daily limits including fees, invalid/oversized requests, stored-refusal reconciliation after lost responses, contact-list recovery, inquiry/payment queues, mobile-only top-ups, recovering an unreceived confirmation, and resuming a durably authorized operation after a crash.

Final handoff gate: **233 tests passed**; **68/68 evaluation items passed across 204 runs**, with **0 unsafe executions**. The running local demo was refreshed after the recovery fixes. Live LLM/ASR accuracy and native-speaker review remain pending.
