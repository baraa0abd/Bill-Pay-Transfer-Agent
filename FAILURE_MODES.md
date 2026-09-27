# Failure modes

Each row: what goes wrong, what the agent does, and the test that proves it.

| # | Failure | Handling | User sees | Test |
|---|---|---|---|---|
| 1 | **Ambiguous recipient or biller**: three contacts match "أحمد"; "الكهرباء" matches grid and generator | Never guesses. Asks one question with numbered options. Non-exact fuzzy matches always ask. | List of matching contacts / billers | `tests/test_dialogue.py::test_ahmed`, `::test_electricity` |
| 2 | **Lost response after the debit committed** (network drop, crash) | Missing response is not treated as failure. The draft UUID is the idempotency key; the agent polls the original key and the wallet replays the stored result. Retrying never debits twice. | "Checking the status…" then the real receipt | `tests/test_messages.py::test_unknown_then_reconciled`, `tests/test_idempotency.py::test_fifty_concurrent`, `tests/test_confirm.py::test_double_tap` |
| 3 | **Parser/LLM outage or invalid output** (timeout, bad JSON, invented name or amount) | Falls back to the conservative rule parser. If that also can't parse it: no draft, no debit. Any span not present in the user's text is rejected. | "ما كدرت أفهم الطلب هسه… ما انخصم شي" | `tests/test_dialogue.py::test_parser_outage_fails_closed`, `tests/test_parser.py::test_invented_id_rejected`, `::test_fallback_to_rules_when_llm_down`, `::test_anthropic_refusal_rejected` |
| 4 | **Insufficient balance or daily limit** | Checked before the draft and again inside the atomic wallet transaction (fee included). | Balance, amount and fee, no confirmation card | `tests/test_dialogue.py::test_insufficient`, `tests/test_wallet.py::test_insufficient` |
| 5 | **Stale or tampered confirmation** (expired card, changed amount, another user's draft) | Confirm checks owner, pending state, 120 s expiry and SHA-256 of the draft payload. | Card rejected, nothing executed | `tests/test_confirm.py::test_invalid_draft` |
| 6 | **Misheard voice input** (low confidence, uncertain name/amount) | Transcript is shown; the user must type the corrected request. Spoken "أكد" never confirms. | Transcript + "please type it" | `tests/test_voice.py::test_misheard_name_forces_review` |

Known limits not handled: real process death can leave a lease "in progress" for up to 30 s; the UI stays in status-check rather than claiming failure. Unknown money slang (`ورقة`, `دفتر`) is asked about, never interpreted.
