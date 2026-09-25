# Idempotency proof

Automated against file-backed SQLite, using HTTP requests.

| Scenario | Evidence |
|---|---|
| 50 concurrent requests, one key | One transaction, one 1,250 IQD debit |
| Response dropped after commit | Retry returns original transaction ID; one debit |
| Crash before commit | Rollback then retry; one debit |
| Changed amount, same key | 409 conflict, no second debit |
| Expired lease | Safe reclaim |
| 24-hour cache cleanup | Permanent transaction tombstone replays original receipt |
| Double confirmation | Integration coverage is added in phase 7 |

Run `python -m pytest tests/test_idempotency.py tests/test_faults.py -q`.
