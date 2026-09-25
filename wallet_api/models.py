from datetime import datetime, timezone
from sqlalchemy import Integer, String, Text, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


def now():
    return int(datetime.now(timezone.utc).timestamp())


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    phone: Mapped[str]
    balance_iqd: Mapped[int] = mapped_column(Integer)
    daily_limit_iqd: Mapped[int] = mapped_column(Integer)
    pin_hash: Mapped[str | None]
    __table_args__ = (CheckConstraint('balance_iqd >= 0'),)


class Contact(Base):
    __tablename__ = 'contacts'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    display_name: Mapped[str]
    normalized_name: Mapped[str]
    nickname: Mapped[str | None]
    phone: Mapped[str]


class Biller(Base):
    __tablename__ = 'billers'
    id: Mapped[int] = mapped_column(primary_key=True)
    name_ar: Mapped[str]
    category: Mapped[str]
    provider: Mapped[str]


class UserBiller(Base):
    __tablename__ = 'user_billers'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    biller_id: Mapped[int] = mapped_column(ForeignKey('billers.id'))
    account_number: Mapped[str]
    label: Mapped[str]


class Bill(Base):
    __tablename__ = 'bills'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_biller_id: Mapped[int] = mapped_column(ForeignKey('user_billers.id'))
    period: Mapped[str]
    amount_iqd: Mapped[int]
    due_date: Mapped[str]
    status: Mapped[str] = mapped_column(default='unpaid')


class Transaction(Base):
    __tablename__ = 'transactions'
    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    type: Mapped[str]
    payee_ref: Mapped[str]
    amount_iqd: Mapped[int]
    fee_iqd: Mapped[int]
    status: Mapped[str]
    created_at: Mapped[int] = mapped_column(default=now)
    idempotency_key: Mapped[str]
    __table_args__ = (UniqueConstraint('user_id', 'idempotency_key'),)


class IdempotencyKey(Base):
    __tablename__ = 'idempotency_keys'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    key: Mapped[str]
    request_fingerprint: Mapped[str]
    status: Mapped[str]
    response_json: Mapped[str | None] = mapped_column(Text)
    locked_until: Mapped[int]
    created_at: Mapped[int] = mapped_column(default=now)
    __table_args__ = (UniqueConstraint('user_id', 'key'),)


class Draft(Base):
    __tablename__ = 'drafts'
    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    payload_json: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str]
    status: Mapped[str] = mapped_column(default='pending')
    expires_at: Mapped[int]
    created_at: Mapped[int] = mapped_column(default=now)
    result_json: Mapped[str | None] = mapped_column(Text)


class Conversation(Base):
    __tablename__ = 'conversations'
    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    state_json: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[int] = mapped_column(default=now)

