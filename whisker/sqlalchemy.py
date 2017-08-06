#!/usr/bin/env python
# whisker/sqlalchemy.py

"""
"""

from contextlib import contextmanager
import logging
from typing import Any, Dict, Generator, Tuple

# noinspection PyUnresolvedReferences
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, event,
from sqlalchemy.engine.base import Engine  # for type hints
from sqlalchemy.orm import scoped_session, Session,  sessionmaker

log = logging.getLogger(__name__)


# =============================================================================
# Functions to get SQLAlchemy database session, etc.
# =============================================================================

def get_database_engine(settings: Dict[str, Any],
                        unbreak_sqlite_transactions: bool = True,
                        pool_pre_ping: bool = True) -> Engine:
    """
    The 'settings' object used here is a dictionary with the following keys:
        url  # str
        echo  # bool
        connect_args  # a dictionary
    """
    database_url = settings['url']
    engine = create_engine(
        database_url,
        echo=settings['echo'],
        connect_args=settings['connect_args']
        # pool_pre_ping=pool_pre_ping  # FOR WHEN SQLAlchemy 1.2 RELEASED! ***
    )
    sqlite = database_url.startswith("sqlite:")
    if not sqlite or not unbreak_sqlite_transactions:
        return engine

    # Hook in events to unbreak SQLite transaction support
    # Detailed in sqlalchemy/dialects/sqlite/pysqlite.py; see
    # "Serializable isolation / Savepoints / Transactional DDL"

    # noinspection PyUnusedLocal
    @event.listens_for(engine, "connect")
    def do_connect(dbapi_connection, connection_record):
        # disable pysqlite's emitting of the BEGIN statement entirely.
        # also stops it from emitting COMMIT before any DDL.
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def do_begin(conn):
        # emit our own BEGIN
        conn.execute("BEGIN")

    return engine


# -----------------------------------------------------------------------------
# Plain functions: not thread-aware; generally AVOID these
# -----------------------------------------------------------------------------

# noinspection PyPep8Naming
def get_database_session_thread_unaware(settings: Dict[str, Any]) -> Session:
    log.warning("get_database_session_thread_unaware() called")
    engine = get_database_engine(settings)
    SessionClass = sessionmaker(bind=engine)
    return SessionClass()


@contextmanager
def session_scope_thread_unaware(
        settings: Dict[str, Any]) -> Generator[Session, None, None]:
    log.warning("session_scope_thread_unaware() called")
    # http://docs.sqlalchemy.org/en/latest/orm/session_basics.html#session-faq-whentocreate  # noqa
    session = get_database_session_thread_unaware(settings)
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


# -----------------------------------------------------------------------------
# Thread-scoped versions
# -----------------------------------------------------------------------------
# http://docs.sqlalchemy.org/en/latest/orm/contextual.html
# https://writeonly.wordpress.com/2009/07/16/simple-read-only-sqlalchemy-sessions/  # noqa
# http://docs.sqlalchemy.org/en/latest/orm/session_api.html

# noinspection PyUnusedLocal
def noflush_readonly(*args, **kwargs) -> None:
    log.debug("Attempt to flush a readonly database session blocked")


# noinspection PyPep8Naming
def get_database_engine_session_thread_scope(
        settings: Dict[str, Any],
        readonly: bool = False,
        autoflush: bool = True) -> Tuple[Engine, Session]:
    # The default for a Session is: autoflush=True, autocommit=False
    # http://docs.sqlalchemy.org/en/latest/orm/session_api.html#sqlalchemy.orm.session.Session  # noqa
    if readonly:
        autoflush = False
    engine = get_database_engine(settings)
    session_factory = sessionmaker(bind=engine, autoflush=autoflush)
    SessionClass = scoped_session(session_factory)
    session = SessionClass()
    if readonly:
        session.flush = noflush_readonly
    return engine, session


def get_database_session_thread_scope(*args, **kwargs) -> Session:
    engine, session = get_database_engine_session_thread_scope(*args, **kwargs)
    return session


@contextmanager
def session_thread_scope(
        settings: Dict[str, Any],
        readonly: bool = False) -> Generator[Session, None, None]:
    session = get_database_session_thread_scope(settings, readonly)
    try:
        yield session
        if not readonly:
            session.commit()
    except:
        if not readonly:
            session.rollback()
        raise
    finally:
        session.close()


# =============================================================================
# Info functions
# =============================================================================

def database_is_sqlite(dbsettings: Dict[str, str]) -> bool:
    database_url = dbsettings['url']
    return database_url.startswith("sqlite:")


def database_is_postgresql(dbsettings: Dict[str, str]) -> bool:
    database_url = dbsettings['url']
    return database_url.startswith("postgresql")
    # ignore colon, since things like "postgresql:", "postgresql+psycopg2:"
    # are all OK


def database_is_mysql(dbsettings: Dict[str, str]) -> bool:
    database_url = dbsettings['url']
    return database_url.startswith("mysql")
