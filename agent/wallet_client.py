import random
import time
import httpx


class WalletClient:
    """Transport injected for offline tests; never invent a new key on retry."""
    def __init__(self, transport, attempts=4, sleep=time.sleep):
        self.transport, self.attempts, self.sleep = transport, attempts, sleep

    def lookup(self, user_id, key):
        try:
            r = self.transport.get(f'/transactions/by-key/{key}', params={'user_id': user_id})
            if r.status_code == 200:
                return r.json()
        except (httpx.TransportError, TimeoutError, RuntimeError):
            pass
        return {'code': 'STATUS_UNKNOWN'}

    def execute(self, kind, payload, key, fault=None):
        for attempt in range(self.attempts):
            try:
                headers = {'Idempotency-Key': key}
                if fault and attempt == 0:
                    headers['X-Fault'] = fault
                r = self.transport.post('/transfers' if kind == 'transfer' else '/bill-payments', json=payload, headers=headers)
                result = r.json()
                if r.status_code < 500 and result.get('code') != 'IN_PROGRESS':
                    return result
            except (httpx.TransportError, TimeoutError, RuntimeError):
                pass
            self.sleep(min(0.05 * 2 ** attempt + random.uniform(0, 0.02), 1))
        return self.lookup(payload['user_id'], key)
