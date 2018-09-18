#!/usr/bin/env python
# whisker/debug_qt.py

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

**Functions to debug Qt objects and signals under PyQt5.**

- See http://stackoverflow.com/questions/2045352

"""


import logging
import threading
from typing import Any, Callable

# noinspection PyPackageRequirements
from PyQt5.QtCore import QObject, QThread
from PyQt5.QtCore import pyqtBoundSignal

log = logging.getLogger(__name__)

TYPE_CONNECT_FN = Callable[[Any], None]
TYPE_DISCONNECT_FN = Callable[[Any], None]
TYPE_EMIT_FN = Callable[[Any], None]

_old_connect = pyqtBoundSignal.connect  # normal method
_old_disconnect = pyqtBoundSignal.disconnect  # normal method
_old_emit = pyqtBoundSignal.emit  # normal method


def _wrap_connect(callable_object):
    """
    Returns a wrapped call to the old version of
    :func:`pyqtBoundSignal.connect`.
    """

    def call(self, *args, **kwargs) -> None:
        callable_object(self, *args, **kwargs)
        _old_connect(self, *args, **kwargs)

    return call


def _wrap_disconnect(callable_object):
    """
    Returns a wrapped call to the old version of
    :func:`pyqtBoundSignal.disconnect`.
    """

    def call(self, *args, **kwargs) -> None:
        callable_object(self, *args, **kwargs)
        _old_disconnect(self, *args, **kwargs)

    return call


def _wrap_emit(callable_object):
    """
    Returns a wrapped call to the old version of
    :func:`pyqtBoundSignal.emit`.
    """

    def call(self, *args) -> None:
        callable_object(self, *args)
        _old_emit(self, *args)

    return call


def enable_signal_debugging(connect_call: TYPE_CONNECT_FN = None,
                            disconnect_call: TYPE_DISCONNECT_FN = None,
                            emit_call: TYPE_EMIT_FN = None) -> None:
    """
    Call this to enable PySide/Qt signal debugging. This will trap all
    :func:`connect` and :func:`disconnect` calls, calling the user-supplied
    functions first and then the real things.
    """

    # noinspection PyUnusedLocal
    def cd(*args, **kwargs) -> None:
        pass

    # noinspection PyUnusedLocal
    def e(*args) -> None:
        pass

    connect_call = connect_call or cd
    disconnect_call = disconnect_call or cd
    emit_call = emit_call or e

    pyqtBoundSignal.connect = _wrap_connect(connect_call)
    pyqtBoundSignal.disconnect = _wrap_disconnect(disconnect_call)
    pyqtBoundSignal.emit = _wrap_emit(emit_call)


def simple_connect_debugger(*args) -> None:
    """
    Function to report on :func:`connect` calls.
    """
    log.debug("CONNECT: signal={s}, args={a}".format(
        s=args[0],
        a=args[1:]
    ))


def simple_emit_debugger(*args) -> None:
    """
    Function to report on :func:`emit` calls.
    """
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
    """
    Enables Qt signal debugging for :func:`connect` and :func:`emit` calls.
    """
    enable_signal_debugging(connect_call=simple_connect_debugger,
                            emit_call=simple_emit_debugger)


def debug_object(obj: QObject) -> None:
    """
    Writes a debug log message within information about the QObject.
    """
    log.debug("Object {} belongs to QThread {}".format(obj, obj.thread()))
    # Does nothing if library compiled in release mode:
    # log.debug("... dumpObjectInfo: {}".format(obj.dumpObjectInfo()))
    # log.debug("... dumpObjectTree: {}".format(obj.dumpObjectTree()))


def debug_thread(thread: QThread) -> None:
    """
    Writes a debug log message about the QThread.
    """
    log.debug("QThread {}".format(thread))
