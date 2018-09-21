#!/usr/bin/env python
# whisker/sqlalchemy.py

"""
===============================================================================

    Copyright (C) 2011-2018 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of the Whisker Python client library.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

===============================================================================

**SQLAlchemy helper functions for Whisker tasks.**

"""

from contextlib import contextmanager
import logging
from typing import Any, Dict, Generator, Tuple

from sqlalchemy import create_engine, event
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
    Get an SQLAlchemy database :class:`Engine` from a simple definition.

    Args:
        settings: a dictionary with the following keys:

            - ``url``: a string
            - ``echo``: a boolean
            - ``connect_args``: a dictionary

            All are passed to SQLAlchemy's :func:`create_engine` function.

        unbreak_sqlite_transactions: hook in events to unbreak SQLite
            transaction support? (Detailed in
            ``sqlalchemy/dialects/sqlite/pysqlite.py``; see "Serializable
            isolation / Savepoints / Transactional DDL".)

        pool_pre_ping: boolean; requires SQLAlchemy 1.2

    Returns:
        an SQLAlchemy :class:`Engine`

    """
    database_url = settings['url']
    engine = create_engine(
        database_url,
        echo=settings['echo'],
        connect_args=settings['connect_args'],
        pool_pre_ping=pool_pre_ping  # requires SQLAlchemy 1.2
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
    """
    Returns an SQLAlchemy database session.

    .. warning:: DEPRECATED: this function is not thread-aware.

    Args:
        settings: passed to :func:`get_database_engine`

    Returns:
        an SQLAlchemy :class:`Session`

    """
    log.warning("get_database_session_thread_unaware() called")
    engine = get_database_engine(settings)
    SessionClass = sessionmaker(bind=engine)
    return SessionClass()


@contextmanager
def session_scope_thread_unaware(
        settings: Dict[str, Any]) -> Generator[Session, None, None]:
    """
    Context manager to provide an SQLAlchemy database session (which
    executes a ``COMMIT`` on success or a ``ROLLBACK`` on failure).

    .. warning:: DEPRECATED: this function is not thread-aware.

    Args:
        settings: passed to :func:`get_database_session_thread_unaware`

    Yields:
        an SQLAlchemy :class:`Session`

    """
    log.warning("session_scope_thread_unaware() called")
    # http://docs.sqlalchemy.org/en/latest/orm/session_basics.html#session-faq-whentocreate  # noqa
    session = get_database_session_thread_unaware(settings)
    # noinspection PyPep8
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
    """
    Does nothing, and is thereby used to block a database session flush.
    """
    log.debug("Attempt to flush a readonly database session blocked")


# noinspection PyPep8Naming
def get_database_engine_session_thread_scope(
        settings: Dict[str, Any],
        readonly: bool = False,
        autoflush: bool = True) -> Tuple[Engine, Session]:
    """
    Gets a thread-scoped SQLAlchemy :class:`Engine` and :class:`Session`.

    Args:
        settings: passed to :func:`get_database_engine`
        readonly: make the session read-only?
        autoflush: passed to :func:`sessionmaker`

    Returns:
        tuple: ``(engine, session)``

    """
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
    """
    Gets a thread-scoped SQLAlchemy :class:`Session`.

    Args:
        args: positional arguments to
            :func:`get_database_engine_session_thread_scope`
        kwargs: keyword arguments to
            :func:`get_database_engine_session_thread_scope`

    Returns:
        the session

    """
    engine, session = get_database_engine_session_thread_scope(*args, **kwargs)
    return session


@contextmanager
def session_thread_scope(
        settings: Dict[str, Any],
        readonly: bool = False) -> Generator[Session, None, None]:
    """
    Context manager to provide a thread-safe SQLAlchemy database session (which
    executes a ``COMMIT`` on success or a ``ROLLBACK`` on failure).

    Args:
        settings: passed to :func:`get_database_session_thread_scope`
        readonly: passed to :func:`get_database_session_thread_scope`

    Yields:
        an SQLAlchemy :class:`Session`

    """
    session = get_database_session_thread_scope(settings, readonly)
    # noinspection PyPep8
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
    """
    Checks the URL in ``dbsettings['url']``: is it an SQLite database?
    """
    database_url = dbsettings['url']
    return database_url.startswith("sqlite:")


def database_is_postgresql(dbsettings: Dict[str, str]) -> bool:
    """
    Checks the URL in ``dbsettings['url']``: is it a PostgreSQL database?
    """
    database_url = dbsettings['url']
    return database_url.startswith("postgresql")
    # ignore colon, since things like "postgresql:", "postgresql+psycopg2:"
    # are all OK


def database_is_mysql(dbsettings: Dict[str, str]) -> bool:
    """
    Checks the URL in ``dbsettings['url']``: is it a MySQL database?
    """
    database_url = dbsettings['url']
    return database_url.startswith("mysql")
