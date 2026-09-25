import os
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


def make_engine(url=None):
    engine = create_engine(url or os.getenv('DATABASE_URL', 'sqlite:///wallet.db'),
                           connect_args={'check_same_thread': False, 'timeout': 30})

    @event.listens_for(engine, 'connect')
    def configure(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA busy_timeout=30000')
        connection.execute('PRAGMA journal_mode=WAL')
    return engine


@contextmanager
def immediate(engine):
    with Session(engine) as session:
        session.connection().exec_driver_sql('BEGIN IMMEDIATE')
        try:
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise

