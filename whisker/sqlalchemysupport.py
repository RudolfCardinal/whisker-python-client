#!/usr/bin/env python
# whisker/sqlalchemysupport.py

from collections import Iterable
from contextlib import contextmanager
import datetime
import logging
log = logging.getLogger(__name__)
import os

arrow = None
try:
    import arrow
except:
    pass

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.runtime.environment import EnvironmentContext
from alembic.script import ScriptDirectory
from sqlalchemy import (
    create_engine,
    event,
)
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import (
    class_mapper,
    scoped_session,
    sessionmaker,
)
from sqlalchemy.types import DateTime, TypeDecorator
import sqlalchemy.dialects.mssql
import sqlalchemy.dialects.mysql

from .exceptions import ImproperlyConfigured
from .lang import OrderedNamespace


# =============================================================================
# Constants for Alembic
# =============================================================================
# https://alembic.readthedocs.org/en/latest/naming.html

ALEMBIC_NAMING_CONVENTION = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    # "ck": "ck_%(table_name)s_%(constraint_name)s",  # too long?
    # ... https://groups.google.com/forum/#!topic/sqlalchemy/SIT4D8S9dUg
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}


# =============================================================================
# Alembic revision/migration system
# =============================================================================
# http://stackoverflow.com/questions/24622170/using-alembic-api-from-inside-application-code  # noqa

def get_head_revision_from_alembic(alembic_config_filename,
                                   alembic_base_dir=None):
    """
    Ask Alembic what its head revision is.
    Arguments:
        base_dir: directory to start in, so relative paths in the config
            file work.
    """
    if alembic_base_dir is None:
        alembic_base_dir = os.path.dirname(alembic_config_filename)
    os.chdir(alembic_base_dir)  # so the directory in the config file works
    config = Config(alembic_config_filename)
    script = ScriptDirectory.from_config(config)
    return script.get_current_head()


def get_current_revision(database_url):
    """
    Ask the database what its current revision is.
    """
    engine = create_engine(database_url)
    conn = engine.connect()
    mig_context = MigrationContext.configure(conn)
    return mig_context.get_current_revision()


def get_current_and_head_revision(database_url, alembic_config_filename,
                                  alembic_base_dir=None):
    # Where we are
    head_revision = get_head_revision_from_alembic(
        alembic_config_filename, alembic_base_dir)
    log.info("Intended database version: {}".format(head_revision))

    # Where we want to be
    current_revision = get_current_revision(database_url)
    log.info("Current database version: {}".format(current_revision))

    # Are we where we want to be?
    return (current_revision, head_revision)


def upgrade_database(alembic_config_filename, alembic_base_dir=None):
    """
    Use Alembic to upgrade our database.

    See http://alembic.readthedocs.org/en/latest/api/runtime.html
    but also, in particular, site-packages/alembic/command.py
    """

    if alembic_base_dir is None:
        alembic_base_dir = os.path.dirname(alembic_config_filename)
    os.chdir(alembic_base_dir)  # so the directory in the config file works
    config = Config(alembic_config_filename)
    script = ScriptDirectory.from_config(config)

    revision = 'head'  # where we want to get to

    def upgrade(rev, context):
        return script._upgrade_revs(revision, rev)

    log.info(
        "Upgrading database to revision '{}' using Alembic".format(revision))

    with EnvironmentContext(config,
                            script,
                            fn=upgrade,
                            as_sql=False,
                            starting_rev=None,
                            destination_rev=revision,
                            tag=None):
        script.run_env()

    log.info("Database upgrade completed")


# =============================================================================
# Functions to get SQLAlchemy database session, etc.
# =============================================================================

def get_database_engine(settings, unbreak_sqlite_transactions=True):
    database_url = settings['url']
    engine = create_engine(database_url,
                           echo=settings['echo'],
                           connect_args=settings['connect_args'])
    sqlite = database_url.startswith("sqlite:")
    if not sqlite or not unbreak_sqlite_transactions:
        return engine

    # Hook in events to unbreak SQLite transaction support
    # Detailed in sqlalchemy/dialects/sqlite/pysqlite.py; see
    # "Serializable isolation / Savepoints / Transactional DDL"

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

def get_database_session_thread_unaware(settings):
    log.warning("get_database_session_thread_unaware() called")
    engine = get_database_engine(settings)
    Session = sessionmaker(bind=engine)
    return Session()


@contextmanager
def session_scope_thread_unaware(settings):
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

def noflush_readonly(*args, **kwargs):
    log.debug("Attempt to flush a readonly database session blocked")


def get_database_session_thread_scope(settings, readonly=False,
                                      autoflush=True):
    if readonly:
        autoflush = False
    engine = get_database_engine(settings)
    session_factory = sessionmaker(bind=engine, autoflush=autoflush)
    Session = scoped_session(session_factory)
    session = Session()
    if readonly:
        session.flush = noflush_readonly
    return session


@contextmanager
def session_thread_scope(settings, readonly=False):
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
# Mixin to:
# - get plain dictionary-like object (with attributes so we can use x.y rather
#   than x['y']) from an SQLAlchemy ORM object
# - make a nice repr() default, maintaining field order
# =============================================================================

class SqlAlchemyAttrDictMixin(object):
    # See http://stackoverflow.com/questions/2537471
    # but more: http://stackoverflow.com/questions/2441796
    def get_attrdict(self):
        """
        Returns what looks like a plain object with the values of the
        SQLAlchemy ORM object.
        """
        columns = self.__table__.columns.keys()
        values = (getattr(self, x) for x in columns)
        zipped = zip(columns, values)
        return OrderedNamespace(zipped)

    def __repr__(self):
        return "<{classname}({kvp})>".format(
            classname=type(self).__name__,
            kvp=", ".join("{}={}".format(k, repr(v))
                          for k, v in self.get_attrdict().items())
        )

    @classmethod
    def from_attrdict(cls, attrdict):
        """
        Builds a new instance of the ORM object from values in an attrdict.
        """
        dictionary = attrdict.__dict__
        return cls(**dictionary)


# =============================================================================
# Info functions
# =============================================================================

def database_is_sqlite(dbsettings):
    database_url = dbsettings['url']
    return database_url.startswith("sqlite:")


def database_is_postgresql(dbsettings):
    database_url = dbsettings['url']
    return database_url.startswith("postgresql")
    # ignore colon, since things like "postgresql:", "postgresql+psycopg2:"
    # are all OK


def database_is_mysql(dbsettings):
    database_url = dbsettings['url']
    return database_url.startswith("mysql")


# =============================================================================
# deepcopy an SQLAlchemy object
# =============================================================================
# Use case: object X is in the database; we want to clone it to object Y,
# which we can then save to the database, i.e. copying all SQLAlchemy field
# attributes of X except its PK. We also want it to copy anything that is
# dependent upon X, i.e. traverse relationships.
#
# https://groups.google.com/forum/#!topic/sqlalchemy/wb2M_oYkQdY
# https://groups.google.com/forum/#!searchin/sqlalchemy/cascade%7Csort:date/sqlalchemy/eIOkkXwJ-Ms/JLnpI2wJAAAJ  # noqa

def walk(obj):
    stack = [obj]
    seen = set()
    while stack:
        obj = stack.pop(0)
        if obj in seen:
            continue
        else:
            seen.add(obj)
            yield obj
        insp = inspect(obj)
        for relationship in insp.mapper.relationships:
            related = getattr(obj, relationship.key)
            if relationship.uselist:
                stack.extend(related)
            elif related is not None:
                stack.append(related)


def copy_sqla_object(obj):
    cls = type(obj)
    mapper = class_mapper(cls)
    newobj = cls()  # not: cls.__new__(cls)
    pk_keys = set([c.key for c in mapper.primary_key])
    for k in [p.key for p in mapper.iterate_properties
              if p.key not in pk_keys]:
        log.debug("copy_sqla_object: processing attribute {}".format(k))
        try:
            setattr(newobj, k, getattr(obj, k))
        except AttributeError:
            pass
    return newobj


def deepcopy_sqla_object(obj, session):
    newobj = None
    for part in walk(obj):
        log.debug("deepcopy_sqla_object: copying {}".format(part))
        newpart = copy_sqla_object(part)
        if newobj is None:
            # The first thing that comes back from walk() is the starting point
            newobj = newpart
        session.add(newpart)
    return newobj


# =============================================================================
# ArrowType that uses fractional second support in MySQL
# =============================================================================

class ArrowMicrosecondType(TypeDecorator):
    """
    Based on ArrowType from SQLAlchemy-Utils, but copes with fractional seconds
    under MySQL 5.6.4+.
    """
    impl = DateTime
    # RNC: For MySQL, need to use sqlalchemy.dialects.mysql.DATETIME(fsp=6);
    # see load_dialect_impl() below.

    def __init__(self, *args, **kwargs):
        if not arrow:
            raise ImproperlyConfigured(
                "'arrow' package is required to use 'ArrowMicrosecondType'")
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):  # RNC
        if dialect.name == 'mysql':
            return dialect.type_descriptor(
                sqlalchemy.dialects.mysql.DATETIME(fsp=6))
        elif dialect.name == 'mssql':  # Microsoft SQL Server
            return dialect.type_descriptor(sqlalchemy.dialects.mssql.DATETIME2)
        else:
            return dialect.type_descriptor(self.impl)

    def process_bind_param(self, value, dialect):
        if value:
            return self._coerce(value).to('UTC').naive
            # RNC: unfortunately... can't store and retrieve timezone, see docs
        return value

    def process_result_value(self, value, dialect):
        if value:
            return arrow.get(value)
        return value

    def process_literal_param(self, value, dialect):
        return str(value)

    def _coerce(self, value):
        if value is None:
            return None
        elif isinstance(value, str):  # RNC
            value = arrow.get(value)
        elif isinstance(value, Iterable):
            value = arrow.get(*value)
        elif isinstance(value, datetime.datetime):  # RNC trivial change
            value = arrow.get(value)
        return value

    def coercion_listener(self, target, value, oldvalue, initiator):
        return self._coerce(value)

    @property
    def python_type(self):
        return self.impl.type.python_type
