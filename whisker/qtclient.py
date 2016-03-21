#!/usr/bin/env python
# whisker/qtclient.py
# Copyright (c) Rudolf Cardinal (rudolf@pobox.com).
# See LICENSE for details.

"""
Multithreaded framework for Whisker Python clients using Qt.

Author: Rudolf Cardinal (rudolf@pobox.com)
Created: late 2016
Last update: 10 Feb 2016

~~~

Note funny bug: data sometimes sent twice.
Looks like it might be this:
http://www.qtcentre.org/threads/29462-QTcpSocket-sends-data-twice-with-flush()

Attempted solution:
- change QTcpSocket() to QTcpSocket(parent=self), in case the socket wasn't
  getting moved between threads properly -- didn't fix
- disable flush() -- didn't fix.
- ... send function is only being called once, according to log
- ... adding thread ID information to the log shows that whisker_controller
  events are coming from two threads...

- ... anyway, bug was this:
    http://stackoverflow.com/questions/34125065
    https://bugreports.qt.io/browse/PYSIDE-249

- Source:
  http://code.qt.io/cgit/qt/qtbase.git/tree/src/corelib/kernel/qobject.h?h=5.4
  http://code.qt.io/cgit/qt/qtbase.git/tree/src/corelib/kernel/qobject.cpp?h=5.4  # noqa
"""

from enum import Enum
import logging

import arrow
from PySide.QtCore import (
    QObject,
    Qt,
    QThread,
    Signal,
)
from PySide.QtNetwork import (
    QAbstractSocket,
    QTcpSocket,
)

from whisker.api import (
    CODE_REGEX,
    EOL,
    EOL_LEN,
    EVENT_REGEX,
    IMMPORT_REGEX,
    PING,
    PING_ACK,
    RESPONSE_SUCCESS,
    TIMESTAMP_REGEX,
    WhiskerApi,
)
from whisker.constants import DEFAULT_PORT
# from whisker.debug_qt import debug_object, debug_thread
from whisker.exceptions import WhiskerCommandFailed
from whisker.lang import CompiledRegexMemory
from whisker.qt import exit_on_exception, StatusMixin

log = logging.getLogger(__name__)

INFINITE_WAIT = -1


class ThreadOwnerState(Enum):
    stopped = 0
    starting = 1
    running = 2
    stopping = 3


def is_socket_connected(socket):
    return (socket and socket.state() == QAbstractSocket.ConnectedState)


def disable_nagle(socket):
    # http://doc.qt.io/qt-5/qabstractsocket.html#SocketOption-enum
    socket.setSocketOption(QAbstractSocket.LowDelayOption, 1)


def get_socket_error(socket):
    return "{}: {}".format(socket.error(), socket.errorString())


def split_timestamp(msg):
    m = TIMESTAMP_REGEX.match(msg)
    if m:
        msg = m.group(1)
        whisker_timestamp = int(m.group(2))
    else:
        whisker_timestamp = None
    return (msg, whisker_timestamp)


def quote(msg):
    """
    Quote for transmission to Whisker.
    Whisker has quite a primitive quoting system...
    Check with strings that actually include quotes.
    """
    return '"{}"'.format(msg)


# =============================================================================
# Object to supervise all Whisker functions
# =============================================================================

class WhiskerOwner(QObject, StatusMixin):
    """
    This object is owned by the GUI thread.
    It devolves work to two other threads:
        (a) main socket listener (WhiskerMainSocketListener)
        (b) task (WhiskerTask)
            + immediate socket (blocking) handler (WhiskerController)

    The use of 'main' here just refers to the main socket (as opposed to the
    immediate socket), not the thread that's doing most of the processing.
    """
    # Outwards, to world/task:
    connected = Signal()
    disconnected = Signal()
    finished = Signal()
    message_received = Signal(str, arrow.Arrow, int)
    event_received = Signal(str, arrow.Arrow, int)
    # Inwards, to possessions:
    controller_finish_requested = Signal()
    mainsock_finish_requested = Signal()
    ping_requested = Signal()
    # And don't forget the signals inherited from StatusMixin.

    def __init__(self, task, server, main_port=DEFAULT_PORT, parent=None,
                 connect_timeout_ms=5000, read_timeout_ms=500,
                 name="whisker_owner", sysevent_prefix='sys_'):
        super().__init__(parent)
        StatusMixin.__init__(self, name, log)
        self.state = ThreadOwnerState.stopped
        self.is_connected = False

        self.mainsockthread = QThread(self)
        self.mainsock = WhiskerMainSocketListener(
            server,
            main_port,
            connect_timeout_ms=connect_timeout_ms,
            read_timeout_ms=read_timeout_ms,
            parent=None)  # must be None as it'll go to a different thread
        self.mainsock.moveToThread(self.mainsockthread)

        self.taskthread = QThread(self)
        self.controller = WhiskerController(server,
                                            sysevent_prefix=sysevent_prefix)
        self.controller.moveToThread(self.taskthread)
        self.task = task
        # debug_object(self)
        # debug_thread(self.taskthread)
        # debug_object(self.controller)
        # debug_object(task)
        self.task.moveToThread(self.taskthread)
        # debug_object(self.controller)
        # debug_object(task)
        self.task.set_controller(self.controller)

        # Connect object and thread start/stop events
        # ... start sequence
        self.taskthread.started.connect(self.task.thread_started)
        self.mainsockthread.started.connect(self.mainsock.start)
        # ... stop
        self.mainsock_finish_requested.connect(self.mainsock.stop,
                                               Qt.DirectConnection)  # NB!
        self.mainsock.finished.connect(self.mainsockthread.quit)
        self.mainsockthread.finished.connect(self.mainsockthread_finished)
        self.controller_finish_requested.connect(self.task.stop)
        self.task.finished.connect(self.controller.task_finished)
        self.controller.finished.connect(self.taskthread.quit)
        self.taskthread.finished.connect(self.taskthread_finished)

        # Status
        self.mainsock.error_sent.connect(self.error_sent)
        self.mainsock.status_sent.connect(self.status_sent)
        self.controller.error_sent.connect(self.error)
        self.controller.status_sent.connect(self.status_sent)
        self.task.error_sent.connect(self.error)
        self.task.status_sent.connect(self.status_sent)

        # Network communication
        self.mainsock.line_received.connect(self.controller.main_received)
        self.controller.connected.connect(self.on_connect)
        self.controller.connected.connect(self.task.on_connect)
        self.controller.message_received.connect(self.message_received)
        self.controller.event_received.connect(self.event_received)
        self.controller.event_received.connect(self.task.on_event)

        # Abort events
        self.mainsock.disconnected.connect(self.on_disconnect)
        self.controller.disconnected.connect(self.on_disconnect)

        # Other
        self.ping_requested.connect(self.controller.ping)

    # -------------------------------------------------------------------------
    # General state control
    # -------------------------------------------------------------------------

    def is_running(self):
        running = self.state != ThreadOwnerState.stopped
        self.debug("is_running: {} (state: {})".format(running,
                                                       self.state.name))
        return running

    def set_state(self, state):
        self.debug("state: {} -> {}".format(self.state, state))
        self.state = state

    def report_status(self):
        self.status("state: {}".format(self.state))
        self.status("connected to server: {}".format(self.is_connected))

    # -------------------------------------------------------------------------
    # Starting
    # -------------------------------------------------------------------------

    def start(self):
        self.debug("WhiskerOwner: start")
        if self.state != ThreadOwnerState.stopped:
            self.error("Can't start: state is: {}".format(self.state.name))
            return
        self.taskthread.start()
        self.mainsockthread.start()
        self.set_state(ThreadOwnerState.running)

    # -------------------------------------------------------------------------
    # Stopping
    # -------------------------------------------------------------------------

    @exit_on_exception
    def on_disconnect(self):
        self.debug("WhiskerOwner: on_disconnect")
        self.is_connected = False
        self.disconnected.emit()
        if self.state == ThreadOwnerState.stopping:
            return
        self.stop()

    def stop(self):
        """Called by the GUI when we want to stop."""
        self.info("Stop requested")
        if self.state == ThreadOwnerState.stopped:
            self.error("Can't stop: state is: {}".format(self.state.name))
            return
        self.set_state(ThreadOwnerState.stopping)
        self.controller_finish_requested.emit()
        self.mainsock_finish_requested.emit()

    @exit_on_exception  # @Slot()
    def mainsockthread_finished(self):
        self.debug("stop: main socket thread stopped")
        self.check_everything_finished()

    @exit_on_exception
    def taskthread_finished(self):
        self.debug("stop: task thread stopped")
        self.check_everything_finished()

    def check_everything_finished(self):
        if self.mainsockthread.isRunning() or self.taskthread.isRunning():
            return
        self.set_state(ThreadOwnerState.stopped)
        self.finished.emit()

    # -------------------------------------------------------------------------
    # Other
    # -------------------------------------------------------------------------

    @exit_on_exception
    def on_connect(self):
        self.status("Fully connected to Whisker server")
        self.is_connected = True
        self.connected.emit()

    def ping(self):
        if not self.is_connected:
            self.warning("Won't ping: not connected")
            return
        self.ping_requested.emit()


# =============================================================================
# Main socket listener
# =============================================================================

class WhiskerMainSocketListener(QObject, StatusMixin):
    finished = Signal()
    disconnected = Signal()
    line_received = Signal(str, arrow.Arrow)

    def __init__(self, server, port, parent=None, connect_timeout_ms=5000,
                 read_timeout_ms=100, name="whisker_mainsocket"):
        super().__init__(parent)
        StatusMixin.__init__(self, name, log)
        self.server = server
        self.port = port
        self.connect_timeout_ms = connect_timeout_ms
        self.read_timeout_ms = read_timeout_ms

        self.finish_requested = False
        self.residual = ''
        self.socket = None
        # Don't create the socket immediately; we're going to be moved to
        # another thread.

    def start(self):
        # Must be separate from __init__, or signals won't be connected yet.
        self.finish_requested = False
        self.status("Connecting to {}:{} with timeout {} ms".format(
            self.server, self.port, self.connect_timeout_ms))
        self.socket = QTcpSocket(self)
        self.socket.disconnected.connect(self.disconnected)
        self.socket.connectToHost(self.server, self.port)
        if not self.socket.waitForConnected(self.connect_timeout_ms):
            errmsg = "Socket error {}".format(get_socket_error(self.socket))
            self.error(errmsg)
            self.finish()
            return
        self.debug("Connected to {}:{}".format(self.server, self.port))
        disable_nagle(self.socket)
        # Main blocking loop
        while not self.finish_requested:
            # self.debug("ping")
            if self.socket.waitForReadyRead(self.read_timeout_ms):
                # data is now ready
                data = self.socket.readAll()
                # readAll() returns a QByteArray; bytes() fails; str() is OK
                data = str(data)
                self.process_data(data)
        self.finish()

    @exit_on_exception
    def stop(self):
        self.debug("WhiskerMainSocketListener: stop")
        self.finish_requested = True

    def sendline_mainsock(self, msg):
        if not is_socket_connected(self.socket):
            self.error("Can't send through a closed socket")
            return
        self.debug("Sending to server (MAIN): {}".format(msg))
        self.socket.write(msg + EOL)
        self.socket.flush()

    def finish(self):
        if is_socket_connected(self.socket):
            self.socket.close()
        self.finished.emit()

    def process_data(self, data):
        """
        Adds the incoming data to any stored residual, splits it into lines,
        and sends each line on to the receiver.
        """
        # self.debug("incoming: {}".format(repr(data)))
        timestamp = arrow.now()
        data = self.residual + data
        fragments = data.split(EOL)
        lines = fragments[:-1]
        self.residual = fragments[-1]
        for line in lines:
            self.debug("incoming line: {}".format(line))
            if line == PING:
                self.sendline_mainsock(PING_ACK)
                self.status("Ping received from server")
                return
            self.line_received.emit(line, timestamp)


# =============================================================================
# Object to talk to task and to immediate socket
# =============================================================================

class WhiskerController(QObject, StatusMixin, WhiskerApi):
    finished = Signal()
    connected = Signal()
    disconnected = Signal()
    message_received = Signal(str, arrow.Arrow, int)
    event_received = Signal(str, arrow.Arrow, int)

    def __init__(self, server, parent=None, connect_timeout_ms=5000,
                 read_timeout_ms=500, name="whisker_controller",
                 sysevent_prefix="sys_"):
        super().__init__(parent)
        StatusMixin.__init__(self, name, log)
        WhiskerApi.__init__(self, whisker_immsend_fn=self.command)
        self.server = server
        self.connect_timeout_ms = connect_timeout_ms
        self.read_timeout_ms = read_timeout_ms

        self.immport = None
        self.code = None
        self.immsocket = None
        self.residual = ''

    @exit_on_exception
    def main_received(self, msg, timestamp):
        gre = CompiledRegexMemory()
        # self.debug("main_received: {}".format(msg))

        # 0. Ping has already been dealt with.
        # 1. Deal with immediate socket connection internally.
        if gre.search(IMMPORT_REGEX, msg):
            self.immport = int(gre.group(1))
            return

        if gre.search(CODE_REGEX, msg):
            code = gre.group(1)
            self.immsocket = QTcpSocket(self)
            self.immsocket.disconnected.connect(self.disconnected)
            self.debug(
                "Connecting immediate socket to {}:{} with timeout {}".format(
                    self.server, self.immport, self.connect_timeout_ms))
            self.immsocket.connectToHost(self.server, self.immport)
            if not self.immsocket.waitForConnected(self.connect_timeout_ms):
                errmsg = "Immediate socket error {}".format(
                    get_socket_error(self.immsocket))
                self.error(errmsg)
                self.finish()
            self.debug("Connected immediate socket to "
                       "{}:{}".format(self.server, self.immport))
            disable_nagle(self.immsocket)
            self.command("Link {}".format(code))
            self.connected.emit()
            return

        # 2. Get timestamp.
        (msg, whisker_timestamp) = split_timestamp(msg)

        # 3. Send the message to a general-purpose receiver
        self.message_received.emit(msg, timestamp, whisker_timestamp)

        # 4. Send the message to specific-purpose receivers.
        if gre.search(EVENT_REGEX, msg):
            event = gre.group(1)
            if self.process_backend_event(event):
                return
            self.event_received.emit(event, timestamp, whisker_timestamp)

    @exit_on_exception
    def task_finished(self):
        self.debug("Task reports that it is finished")
        self.close_immsocket()
        self.finished.emit()

    def sendline_immsock(self, msg):
        self.debug("Sending to server (IMM): {}".format(msg))
        self.immsocket.write(msg + EOL)
        self.immsocket.waitForBytesWritten(INFINITE_WAIT)
        # http://doc.qt.io/qt-4.8/qabstractsocket.html
        self.immsocket.flush()

    def getline_immsock(self):
        """Get one line from the socket. Blocking."""
        data = self.residual
        while EOL not in data:
            # self.debug("WAITING FOR DATA")
            # get more data from socket
            self.immsocket.waitForReadyRead(INFINITE_WAIT)
            # self.debug("DATA READY. READING IT.")
            data += str(self.immsocket.readAll())
            # self.debug("OK; HAVE READ DATA.")
            # self.debug("DATA: {}".format(repr(data)))
        eol_index = data.index(EOL)
        line = data[:eol_index]
        self.residual = data[eol_index + EOL_LEN:]
        # self.debug("LINE: {}".format(line))
        return line

    def get_response_with_timestamp(self, msg):
        if not self.is_connected():
            self.error("Not connected")
            return (None, None)
        self.sendline_immsock(msg)
        reply = self.getline_immsock()
        (reply, whisker_timestamp) = split_timestamp(reply)
        self.debug("Immediate socket reply (timestamp={}): {}".format(
            whisker_timestamp, reply))
        return (reply, whisker_timestamp)

    def get_response(self, msg):
        (reply, whisker_timestamp) = self.get_response_with_timestamp(msg)
        return reply

    def get_command_boolean(self, msg):
        reply = self.get_response(msg)
        success = reply == RESPONSE_SUCCESS
        # self.debug("get_command_boolean: {} -> {}".format(msg, success))
        return success

    def command(self, *args):
        msg = " ".join(str(x) for x in args)
        return self.get_command_boolean(msg)

    def command_exc(self, *args):
        """Complete command or raise WhiskerCommandFailed."""
        msg = " ".join(str(x) for x in args)
        if not self.command(msg):
            raise WhiskerCommandFailed(msg)

    def is_connected(self):
        return is_socket_connected(self.immsocket)
        # ... if the immediate socket is running, the main socket should be

    def close_immsocket(self):
        if is_socket_connected(self.immsocket):
            self.immsocket.close()

    @exit_on_exception
    def ping(self):
        reply = self.get_response(PING)
        if reply:
            self.status("Successfully pinged server")
        else:
            self.status("Failed to ping server")

    def send_to_client(self, clientnum, msg):
        return self.command("SendToClient {} {}".format(clientnum, quote(msg)))

    def broadcast(self, msg):
        return self.send_to_client(-1, msg)


# =============================================================================
# Object from which Whisker tasks should be subclassed
# =============================================================================

class WhiskerTask(QObject, StatusMixin):
    finished = Signal()  # emit from stop() function when all done

    def __init__(self, parent=None, name="whisker_task"):
        super().__init__(parent)
        StatusMixin.__init__(self, name, log)
        self.whisker = None

    def set_controller(self, controller):
        """
        Called by WhiskerOwner. No need to override.
        """
        self.whisker = controller

    def thread_started(self):
        """
        Slot called from WhiskerOwner.taskthread.started signal, which is
        called indirectly by WhiskerOwner.start().
        Use this for additional setup if required.
        No need to override in simple situations.
        """
        pass

    def stop(self):
        """
        Called by the WhiskerOwner when we should stop.
        When we've done what we need to, emit finished.
        No need to override in simple situations.
        """
        self.debug("WhiskerTask: stopping")
        self.finished.emit()

    @exit_on_exception
    def on_connect(self):
        """
        The WhiskerOwner makes this slot get called when the
        WhiskerController is connected.
        """
        self.warning("on_connect: YOU SHOULD OVERRIDE THIS")

    @exit_on_exception  # @Slot(str, arrow.Arrow, int)
    def on_event(self, event, timestamp, whisker_timestamp_ms):
        """The WhiskerController event_received signal comes here."""
        # You should override this
        msg = "SHOULD BE OVERRIDDEN. EVENT: {}".format(event)
        self.status(msg)
