import time
from .errors import WalletError


class Faults:
    def __init__(self, mode=None, enabled=False):
        self.mode = mode if enabled else None

    def before(self):
        if self.mode == 'BILLER_DOWN':
            raise WalletError('BILLER_UNAVAILABLE')
        if self.mode and self.mode.startswith('DELAY_MS='):
            time.sleep(min(int(self.mode.split('=')[1]), 3000) / 1000)

    def before_commit(self):
        if self.mode == 'CRASH_BEFORE_COMMIT':
            raise RuntimeError('simulated crash')

    def after_commit(self):
        if self.mode == 'DROP_RESPONSE_AFTER_COMMIT':
            raise TimeoutError('simulated lost response')
