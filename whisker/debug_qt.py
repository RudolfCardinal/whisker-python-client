#!/usr/bin/env python
# starfeeder/debug_qt.py
# Copyright (c) Rudolf Cardinal (rudolf@pobox.com).
# See LICENSE for details.

# See: http://stackoverflow.com/questions/2045352

import logging
import threading

# noinspection PyPackageRequirements
from PyQt5.QtCore import QObject, QThread

log = logging.getLogger(__name__)

_old_connect = QObject.connect  # staticmethod
_old_disconnect = QObject.disconnect  # staticmethod
_old_emit = QObject.emit  # normal method


def _wrap_connect(callable_object):
    """Returns a wrapped call to the old version of QObject.connect"""

    # noinspection PyDecorator
    @staticmethod
    def call(*args):
        callable_object(*args)
        _old_connect(*args)
    return call


def _wrap_disconnect(callable_object):
    """
    Returns a wrapped call to the old version of QObject.disconnect
    """

    # noinspection PyDecorator
    @staticmethod
    def call(*args):
        callable_object(*args)
        _old_disconnect(*args)
    return call


def enable_signal_debugging(**kwargs) -> None:
    """Call this to enable PySide/Qt Signal debugging. This will trap all
    connect, and disconnect calls."""

    # noinspection PyUnusedLocal
    def f(*args):
        return None

    connect_call = kwargs.get('connect_call', f)
    disconnect_call = kwargs.get('disconnect_call', f)
    emit_call = kwargs.get('emit_call', f)

    QObject.connect = _wrap_connect(connect_call)
    QObject.disconnect = _wrap_disconnect(disconnect_call)

    def new_emit(self, *args):
        emit_call(self, *args)
        _old_emit(self, *args)

    QObject.emit = new_emit


def simple_connect_debugger(*args) -> None:
    log.debug("CONNECT: args={}".format(args))


def simple_emit_debugger(*args) -> None:
    emitter = args[0]
    # emitter_qthread = emitter.thread()
    log.debug(
        "EMIT: emitter={e}, "
        "thread name={n}, signal={s}, args={a}".format(
            e=emitter,
            n=threading.current_thread().name,
            s=repr(args[1]),
            a=repr(args[2:]),
        )
        # emitter's thread={t}, currentThreadId={i}, "
        # t=emitter_qthread,
        # i=emitter_qthread.currentThreadId(),
    )


def enable_signal_debugging_simply() -> None:
    enable_signal_debugging(connect_call=simple_connect_debugger,
                            emit_call=simple_emit_debugger)


def debug_object(obj: QObject) -> None:
    log.debug("Object {} belongs to QThread {}".format(obj, obj.thread()))
    # Does nothing if library compiled in release mode:
    # log.debug("... dumpObjectInfo: {}".format(obj.dumpObjectInfo()))
    # log.debug("... dumpObjectTree: {}".format(obj.dumpObjectTree()))


def debug_thread(thread: QThread) -> None:
    log.debug("QThread {}".format(thread))
