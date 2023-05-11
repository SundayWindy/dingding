from contextvars import ContextVar
from typing import Protocol

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from settings import settings

POSTGRES_SESSION_VAR: ContextVar[AsyncSession] = ContextVar('PostgresSession')
POSTGRES_ENGINE = create_async_engine(settings.database_url)
PostgresSession = sessionmaker(POSTGRES_ENGINE, class_=AsyncSession)

SQLITE_SESSION_VAR: ContextVar[Session] = ContextVar('SqlLiteSession')
SQLITE_ENGINE = create_engine(settings.sqlite_database_url)
SqliteSession = sessionmaker(SQLITE_ENGINE)


class PGSessionMaker(Protocol):
    def __call__(self) -> PostgresSession:
        ...


class SQLiteSessionMaker(Protocol):
    def __call__(self) -> PostgresSession:
        ...


def pg_session_maker() -> PostgresSession:
    try:
        return POSTGRES_SESSION_VAR.get()
    except LookupError:
        session = PostgresSession()
        POSTGRES_SESSION_VAR.set(session)
        return session


def sqlite_session_maker() -> SqliteSession:
    try:
        return SQLITE_SESSION_VAR.get()
    except LookupError:
        session = SqliteSession()
        SQLITE_SESSION_VAR.set(session)
        return session
