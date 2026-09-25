from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class WalletError(Exception):
    def __init__(self, code, detail='', status=400):
        self.code, self.detail, self.status = code, detail or code, status


def install_errors(app: FastAPI):
    @app.exception_handler(WalletError)
    async def wallet_error(request: Request, exc: WalletError):
        return JSONResponse({'code': exc.code, 'detail': exc.detail}, status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc):
        return JSONResponse({'code': 'AMOUNT_INVALID', 'detail': 'Invalid request fields'}, status_code=422)
