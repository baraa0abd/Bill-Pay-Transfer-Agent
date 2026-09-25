from uuid import uuid4
from fastapi import FastAPI, Header
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .db import Base, immediate
from .models import User, Contact, Biller, UserBiller, Bill, Transaction, now
from .schemas import Payment
from .errors import WalletError, install_errors
from .idempotency import execute_once
from .faults import Faults

FEE_IQD = 250


def record(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns if c.name != 'pin_hash'}


def debit(session, payment, kind, key):
    user = session.get(User, payment.user_id)
    if not user:
        raise WalletError('UNKNOWN_USER', status=404)
    if kind == 'transfer':
        contact = session.get(Contact, payment.payee_id)
        if not contact or contact.user_id != user.id or payment.bill_id is not None:
            raise WalletError('UNKNOWN_PAYEE')
        payee_ref = str(contact.id)
    else:
        bill = session.get(Bill, payment.bill_id)
        link = session.get(UserBiller, bill.user_biller_id) if bill else None
        if not link or link.user_id != user.id or payment.payee_id is not None:
            raise WalletError('UNKNOWN_BILLER')
        if bill.status == 'paid':
            raise WalletError('BILL_ALREADY_PAID')
        if payment.amount_iqd != bill.amount_iqd:
            raise WalletError('AMOUNT_INVALID')
        payee_ref = str(bill.id)
    total = payment.amount_iqd + FEE_IQD
    if total > user.balance_iqd:
        raise WalletError('INSUFFICIENT_FUNDS', f'{total}|{user.balance_iqd}')
    spent = session.scalar(select(func.coalesce(func.sum(Transaction.amount_iqd + Transaction.fee_iqd), 0)).where(
        Transaction.user_id == user.id, Transaction.status == 'succeeded', Transaction.created_at >= now() // 86400 * 86400))
    if spent + total > user.daily_limit_iqd:
        raise WalletError('LIMIT_EXCEEDED')
    user.balance_iqd -= total
    transaction = Transaction(id=str(uuid4()), user_id=user.id, type=kind, payee_ref=payee_ref,
        amount_iqd=payment.amount_iqd, fee_iqd=FEE_IQD, status='succeeded', created_at=now(), idempotency_key=key)
    session.add(transaction)
    if kind == 'bill_payment':
        bill.status = 'paid'
    session.flush()
    return {**record(transaction), 'balance_iqd': user.balance_iqd}


def create_wallet(engine, demo_mode=False):
    app = FastAPI(title='Mock wallet')
    install_errors(app)

    @app.get('/users/{user_id}/balance')
    def balance(user_id: int):
        with Session(engine) as s:
            user = s.get(User, user_id)
            if not user:
                raise WalletError('UNKNOWN_USER', status=404)
            return record(user)

    @app.get('/users/{user_id}/contacts')
    def contacts(user_id: int):
        with Session(engine) as s:
            return [record(x) for x in s.scalars(select(Contact).where(Contact.user_id == user_id))]

    @app.get('/users/{user_id}/billers')
    def billers(user_id: int):
        with Session(engine) as s:
            return [{**record(b), **{'user_biller_id': u.id, 'account_number': u.account_number, 'label': u.label}}
                    for b, u in s.execute(select(Biller, UserBiller).join(UserBiller).where(UserBiller.user_id == user_id))]

    @app.get('/users/{user_id}/bills')
    def bills(user_id: int, status: str = 'unpaid'):
        with Session(engine) as s:
            return [record(x) for x in s.scalars(select(Bill).join(UserBiller).where(UserBiller.user_id == user_id, Bill.status == status))]

    @app.get('/users/{user_id}/transactions')
    def transactions(user_id: int):
        with Session(engine) as s:
            return [record(x) for x in s.scalars(select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.created_at.desc()).limit(30))]

    @app.get('/transactions/by-key/{key}')
    def by_key(key: str, user_id: int):
        with Session(engine) as s:
            row = s.scalar(select(Transaction).where(Transaction.user_id == user_id, Transaction.idempotency_key == key))
            if not row:
                raise WalletError('NOT_FOUND', status=404)
            return {**record(row), 'balance_iqd': s.get(User, user_id).balance_iqd}

    @app.post('/transfers')
    def transfer(payment: Payment, idempotency_key: str | None = Header(default=None), x_fault: str | None = Header(default=None)):
        return execute_once(engine, payment, 'transfer', idempotency_key, debit, Faults(x_fault, demo_mode))

    @app.post('/bill-payments')
    def bill_payment(payment: Payment, idempotency_key: str | None = Header(default=None), x_fault: str | None = Header(default=None)):
        return execute_once(engine, payment, 'bill_payment', idempotency_key, debit, Faults(x_fault, demo_mode))
    return app
