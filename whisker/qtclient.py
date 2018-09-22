#!/usr/bin/env python
# whisker/qtclient.py

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

**Multithreaded framework for Whisker Python clients using Qt.**

- Created: late 2016
- Last update: 20 Sep 2018

- Note funny bug: data sometimes sent twice.

  - Looks like it might be this:
    http://www.qtcentre.org/threads/29462-QTcpSocket-sends-data-twice-with-flush()
    
  - Attempted solution:
  
    - change ``QTcpSocket()`` to ``QTcpSocket(parent=self)``, in case the
      socket wasn't getting moved between threads properly -- didn't fix
    - disable ``flush()`` -- didn't fix.
    - send function is only being called once, according to log
    - adding thread ID information to the log shows that ``whisker_controller``
      events are coming from two threads...
      
  - Anyway, bug was this:
  
    - http://stackoverflow.com/questions/34125065
    - https://bugreports.qt.io/browse/PYSIDE-249

- Source:

  - http://code.qt.io/cgit/qt/qtbase.git/tree/src/corelib/kernel/qobject.h?h=5.4
  - http://code.qt.io/cgit/qt/qtbase.git/tree/src/corelib/kernel/qobject.cpp?h=5.4
  
"""  # noqa

import logging
from enum import Enum
from typing import Optional

import arrow
from cardinal_pythonlib.regexfunc import CompiledRegexMemory
# noinspection PyPackageRequirements
from PyQt5.QtCore import (
    QByteArray,
    QObject,
    Qt,
    QThread,
    pyqtSignal,
    pyqtSlot,
)
# noinspection PyPackageRequirements
from PyQt5.QtNetwork import (
    QAbstractSocket,
    QTcpSocket,
)

from whisker.api import (
    CLIENT_MESSAGE_REGEX,
    CODE_REGEX,
    ENCODING,
    EOL,
    EOL_LEN,
    ERROR_REGEX,
    EVENT_REGEX,
    IMMPORT_REGEX,
    KEY_EVENT_REGEX,
    msg_from_args,
    PING,
    PING_ACK,
    split_timestamp,
    SYNTAX_ERROR_REGEX,
    WARNING_REGEX,
    WhiskerApi,
)
from whisker.constants import DEFAULT_PORT
from whisker.qt import exit_on_exception, StatusMixin

log = logging.getLogger(__name__)

INFINITE_WAIT = -1


class ThreadOwnerState(Enum):
    STOPPED = 0
    STARTING = 1
    RUNNING = 2
    STOPPING = 3


def is_socket_connected(socket: QAbstractSocket) -> bool:
    """
    Is the Qt socket connected?
    """
    return socket and socket.state() == QAbstractSocket.ConnectedState


def disable_nagle(socket: QAbstractSocket) -> None:
    """
    Disable the Nagle algorithm on the Qt socket. (This makes it send any
    outbound data immediately, rather than waiting and packaging it up with
    potential subsequent data. So this function chooses a low-latency mode
    over a high-efficiency mode.)
    """
    # http://doc.qt.io/qt-5/qabstractsocket.html#SocketOption-enum
    socket.setSocketOption(QAbstractSocket.LowDelayOption, 1)


def get_socket_error(socket: QAbstractSocket) -> str:
    """
    Returns a textual description of the last error on the specified Qt
    socket.
    """
    return "{}: {}".format(socket.error(), socket.errorString())


def quote(msg: str) -> str:
    """
    Return its argument suitably quoted for transmission to Whisker.

    - Whisker has quite a primitive quoting system...
    - Check with strings that actually include quotes.
    """
    return '"{}"'.format(msg)


# =============================================================================
# Object to supervise all Whisker functions
# =============================================================================

class WhiskerOwner(QObject, StatusMixin):  # GUI thread
    """
    Object to own and manage communication with a Whisker server.

    This object is owned by the GUI thread.
    It devolves work to two other threads:

    (A) **main socket listener** (:class:`WhiskerMainSocketListener`, as the
        instance ``self.mainsock``, in the thread ``self.mainsockthread``);
        
    (B) **task** (:class:`WhiskerQtTask`, as the instance ``self.task`` in the
        thread ``self.taskthread``) + **immediate socket blocking handler**
        (:class:`WhiskerController`, as the instance ``self.controller`` in the
        thread ``self.taskthread``).

    References to "main" here just refers to the main socket (as opposed to the
    immediate socket), not the thread that's doing most of the processing.

    Signals of relevance to users:

    - ``connected()``
    - ``disconnected()``
    - ``finished()``
    - ``message_received(str, arrow.Arrow, int)``
    - ``event_received(str, arrow.Arrow, int)``
    - ``pingack_received(arrow.Arrow, int)``
    """
    # Outwards, to world/task:
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    finished = pyqtSignal()
    message_received = pyqtSignal(str, arrow.Arrow, int)
    event_received = pyqtSignal(str, arrow.Arrow, int)
    pingack_received = pyqtSignal(arrow.Arrow, int)
    # Inwards, to possessions:
    controller_finish_requested = pyqtSignal()
    mainsock_finish_requested = pyqtSignal()
    ping_requested = pyqtSignal()
    # And don't forget the signals inherited from StatusMixin.

    # noinspection PyUnresolvedReferences
    def __init__(self,
                 task: 'WhiskerQtTask',  # forward reference for type hint
                 server: str,
                 main_port: int = DEFAULT_PORT,
                 parent: QObject = None,
                 connect_timeout_ms: int = 5000,
                 read_timeout_ms: int = 500,
                 name: str = "whisker_owner",
                 sysevent_prefix: str = 'sys_',
                 **kwargs) -> None:
        """
        Args:
            task: instance of something derived from :class:`WhiskerQtTask`
            server: host name or IP address of Whisker server
            main_port: main port number for Whisker server
            parent: optional parent :`QObject`
            connect_timeout_ms: time to wait for successful connection (ms)
                before considering it a failure
            read_timeout_ms: time to wait for each read (primary effect is to
                determine the application's responsivity when asked to finish;
                see :class:`WhiskerMainSocketListener`)
            name: (name for :class:`StatusMixin`)
            sysevent_prefix: default system event prefix (for
                :class:`WhiskerController`)
            kwargs: parameters to superclass
        """
        super().__init__(parent=parent, name=name, logger=log, **kwargs)
        self.state = ThreadOwnerState.STOPPED
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
                                               type=Qt.DirectConnection)  # NB!
        self.mainsock.finished.connect(self.mainsockthread.quit)
        self.mainsockthread.finished.connect(self._mainsockthread_finished)
        self.controller_finish_requested.connect(self.task.stop)
        self.task.finished.connect(self.controller.task_finished)
        self.controller.finished.connect(self.taskthread.quit)
        self.taskthread.finished.connect(self._taskthread_finished)

        # Status
        self.mainsock.error_sent.connect(self.error_sent)
        self.mainsock.status_sent.connect(self.status_sent)
        self.controller.error_sent.connect(self.error)
        self.controller.status_sent.connect(self.status_sent)
        self.task.error_sent.connect(self.error)
        self.task.status_sent.connect(self.status_sent)

        # Network communication
        self.mainsock.line_received.connect(self.controller.main_received)
        self.controller.connected.connect(self._on_connect)
        self.controller.connected.connect(self.task.on_connect)
        self.controller.message_received.connect(self.message_received)  # different thread  # noqa
        self.controller.event_received.connect(self.event_received)  # different thread  # noqa
        self.controller.event_received.connect(self.task.on_event)  # same thread  # noqa
        self.controller.key_event_received.connect(self.task.on_key_event)  # same thread  # noqa
        self.controller.client_message_received.connect(self.task.on_client_message)  # same thread  # noqa
        self.controller.pingack_received.connect(self.pingack_received)  # different thread  # noqa
        self.controller.warning_received.connect(self.task.on_warning)  # same thread  # noqa
        self.controller.error_received.connect(self.task.on_error)  # same thread  # noqa
        self.controller.syntax_error_received.connect(
            self.task.on_syntax_error)  # same thread  # noqa

        # Abort events
        self.mainsock.disconnected.connect(self._on_disconnect)
        self.controller.disconnected.connect(self._on_disconnect)

        # Other
        self.ping_requested.connect(self.controller.ping)

    # -------------------------------------------------------------------------
    # General state control
    # -------------------------------------------------------------------------

    def is_running(self) -> bool:
        """
        Are any of our worker threads starting/running/stopping?
        """
        running = self.state != ThreadOwnerState.STOPPED
        self.debug("is_running: {} (state: {})".format(running,
                                                       self.state.name))
        return running

    def _set_state(self, state: ThreadOwnerState) -> None:
        """
        Internal function to set the thread state flag.
        """
        self.debug("state: {} -> {}".format(self.state, state))
        self.state = state

    def report_status(self) -> None:
        """
        Print current thread/server state to the log.
        """
        self.status("state: {}".format(self.state))
        self.status("connected to server: {}".format(self.is_connected))

    # -------------------------------------------------------------------------
    # Starting
    # -------------------------------------------------------------------------

    def start(self) -> None:
        """
        Start our worker threads.
        """
        self.debug("WhiskerOwner: start")
        if self.state != ThreadOwnerState.STOPPED:
            self.error("Can't start: state is: {}".format(self.state.name))
            return
        self.taskthread.start()
        self.mainsockthread.start()
        self._set_state(ThreadOwnerState.RUNNING)

    # -------------------------------------------------------------------------
    # Stopping
    # -------------------------------------------------------------------------

    # noinspection PyArgumentList
    @pyqtSlot()
    @exit_on_exception
    def _on_disconnect(self) -> None:
        """
        Slot called when the Whisker server disconnects.
        """
        self.debug("WhiskerOwner: on_disconnect")
        self.is_connected = False
        self.disconnected.emit()
        if self.state == ThreadOwnerState.STOPPING:
            return
        self.stop()

    def stop(self) -> None:
        """
        Called by the GUI when we want to stop.
        """
        self.info("Stop requested [previous state: {}]".format(
            self.state.name))
        if self.state == ThreadOwnerState.STOPPED:
            self.error("Can't stop: was already stopped")
            return
        self._set_state(ThreadOwnerState.STOPPING)
        self.controller_finish_requested.emit()  # -> self.task.stop
        self.mainsock_finish_requested.emit()  # -> self.mainsock.stop

    # noinspection PyArgumentList
    @pyqtSlot()
    @exit_on_exception
    def _mainsockthread_finished(self) -> None:
        """
        Slot called when our main-socket thread has finished.
        """
        self.debug("stop: main socket thread stopped")
        self._check_everything_finished()

    # noinspection PyArgumentList
    @pyqtSlot()
    @exit_on_exception
    def _taskthread_finished(self) -> None:
        """
        Slot called when our task thread has finished.
        """
        self.debug("stop: task thread stopped")
        self._check_everything_finished()

    def _check_everything_finished(self) -> None:
        """
        Have all out threads finished? If so, emit the ``finished`` signal.
        """
        if self.mainsockthread.isRunning() or self.taskthread.isRunning():
            return
        self._set_state(ThreadOwnerState.STOPPED)
        self.finished.emit()

    # -------------------------------------------------------------------------
    # Other
    # -------------------------------------------------------------------------

    # noinspection PyArgumentList
    @pyqtSlot()
    @exit_on_exception
    def _on_connect(self) -> None:
        """
        Slot called when we are fully connected to the Whisker server.
        """
        self.status("Fully connected to Whisker server")
        self.is_connected = True
        self.connected.emit()

    def ping(self) -> None:
        """
        Pings the Whisker server.
        """
        if not self.is_connected:
            self.warning("Won't ping: not connected")
            return
        self.ping_requested.emit()


# =============================================================================
# Main socket listener
# =============================================================================

class WhiskerMainSocketListener(QObject, StatusMixin):
    """
    Whisker thread (A) (see :class:`WhiskerOwner`).
    Listens to the main socket.
    
    Signals:

    - ``finished()``
    - ``disconnected()``
    - ``line_received(msg: str, timestamp: arrow.Arrow)``
    """
    finished = pyqtSignal()
    disconnected = pyqtSignal()
    line_received = pyqtSignal(str, arrow.Arrow)

    def __init__(self,
                 server: str,
                 port: int,
                 parent: QObject = None,
                 connect_timeout_ms: int = 5000,
                 read_timeout_ms: int = 100,
                 name: str = "whisker_mainsocket",
                 **kwargs) -> None:
        """
        
        Args:
            server: host name or IP address of Whisker server
            port: main port number for Whisker server
            parent: optional parent :`QObject`
            connect_timeout_ms: time to wait for successful connection (ms)
                before considering it a failure
            read_timeout_ms: time to wait for each read (primary effect is to
                determine the application's responsivity when asked to finish;
                see :class:`WhiskerMainSocketListener`)
            name: (name for :class:`StatusMixin`)
            kwargs: parameters to superclass 
        """
        super().__init__(parent=parent, name=name, logger=log, **kwargs)
        self.server = server
        self.port = port
        self.connect_timeout_ms = connect_timeout_ms
        self.read_timeout_ms = read_timeout_ms

        self.finish_requested = False
        self.residual = ''
        self.socket = None
        self.running = False
        # Don't create the socket immediately; we're going to be moved to
        # another thread.

    # noinspection PyArgumentList
    @pyqtSlot()
    def start(self) -> None:
        """
        - Connect to the Whisker server via the main socket.
        - Enter a blocking loop waiting for input and periodically checking
          for a "please finish" signal (with a frequency determined by
          :attr:`read_timeout_ms`.
        - Eventually call :func:`WhiskerMainSocketListener.finish`.
        """
        # Must be separate from __init__, or signals won't be connected yet.
        self.finish_requested = False
        self.status("Connecting to {}:{} with timeout {} ms".format(
            self.server, self.port, self.connect_timeout_ms))
        self.socket = QTcpSocket(self)
        # noinspection PyUnresolvedReferences
        self.socket.disconnected.connect(self.disconnected)
        self.socket.connectToHost(self.server, self.port)
        if not self.socket.waitForConnected(self.connect_timeout_ms):
            errmsg = "Socket error {}".format(get_socket_error(self.socket))
            self.error(errmsg)
            self._finish()
            return
        self.info("Connected to {}:{}".format(self.server, self.port))
        disable_nagle(self.socket)
        # Main blocking loop
        self.running = True
        while not self.finish_requested:
            # self.debug("ping")
            if self.socket.waitForReadyRead(self.read_timeout_ms):
                # data is now ready
                data = self.socket.readAll()  # type: QByteArray
                # log.critical(repr(data))
                # log.critical(repr(type(data)))  # <class 'PyQt5.QtCore.QByteArray'> under PyQt5  # noqa

                # for PySide:
                # - readAll() returns a QByteArray; bytes() fails; str() is OK
                # strdata = str(data)

                # for PyQt5:
                # - readAll() returns a QByteArray again;
                # - however, str(data) looks like "b'Info: ...\\n'"
                strdata = data.data().decode(ENCODING)  # this works

                # log.critical(repr(strdata))
                self._process_data(strdata)
        self.running = False
        self.info("WhiskerMainSocketListener: main event loop complete")
        self._finish()

    # noinspection PyArgumentList
    @pyqtSlot()
    @exit_on_exception
    def stop(self) -> None:
        """
        Stop (by requesting a finish and waiting for the blocking loop in
        :func:`WhiskerMainSocketListener.start` to notice.
        """
        self.debug("WhiskerMainSocketListener: stop")
        if not self.running:
            self.error(
                "WhiskerMainSocketListener: stop requested, but not running")
        self.finish_requested = True

    def _sendline_mainsock(self, msg: str) -> None:
        """
        Send an EOL-terminated message to the server via the main socket.
        """
        if not is_socket_connected(self.socket):
            self.error("Can't send through a closed socket")
            return
        self.debug("Sending to server (MAIN): {}".format(msg))
        final_str = msg + EOL
        data_bytes = final_str.encode(ENCODING)
        self.socket.write(data_bytes)
        self.socket.flush()

    def _finish(self) -> None:
        """
        Clean up and emit the ``finished`` signal.
        """
        if is_socket_connected(self.socket):
            self.socket.close()
        self.info("WhiskerMainSocketListener: finished")
        self.finished.emit()

    def _process_data(self, data: str) -> None:
        """
        Adds the incoming data to any stored residual, splits it into lines,
        and sends each line out via the ``line_received`` signal (on to the
        receiver).
        """
        self.debug("incoming: {}".format(repr(data)))
        timestamp = arrow.now()
        data = self.residual + data
        fragments = data.split(EOL)
        lines = fragments[:-1]
        self.residual = fragments[-1]
        for line in lines:
            self.debug("incoming line: {}".format(line))
            if line == PING:
                self._sendline_mainsock(PING_ACK)
                self.status("Ping received from server")
                return
            self.line_received.emit(line, timestamp)


# =============================================================================
# Object to talk to task and to immediate socket
# =============================================================================

class WhiskerController(QObject, StatusMixin, WhiskerApi):
    """
    Controls the Whisker immediate socket.

    - Encapsulates the Whisker API.
    - Lives in Whisker thread (B) (see :class:`WhiskerOwner`).
    - Emits signals that can be processed by the Whisker task (derived from
      :class:`WhiskerQtTask`).
    
    Signals:

    - ``finished()``
    - ``connected()``
    - ``disconnected()``
    - ``message_received(str, arrow.Arrow, int)``
    - ``event_received(str, arrow.Arrow, int)``
    - ``key_event_received(str, arrow.Arrow, int)``
    - ``client_message_received(int, str, arrow.Arrow, int)``
    - ``warning_received(str, arrow.Arrow, int)``
    - ``syntax_error_received(str, arrow.Arrow, int)``
    - ``error_received(str, arrow.Arrow, int)``
    - ``pingack_received(arrow.Arrow, int)``

    """
    finished = pyqtSignal()
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    message_received = pyqtSignal(str, arrow.Arrow, int)
    event_received = pyqtSignal(str, arrow.Arrow, int)
    key_event_received = pyqtSignal(str, arrow.Arrow, int)
    client_message_received = pyqtSignal(int, str, arrow.Arrow, int)
    warning_received = pyqtSignal(str, arrow.Arrow, int)
    syntax_error_received = pyqtSignal(str, arrow.Arrow, int)
    error_received = pyqtSignal(str, arrow.Arrow, int)
    pingack_received = pyqtSignal(arrow.Arrow, int)

    def __init__(self,
                 server: str,
                 parent: QObject = None,
                 connect_timeout_ms: int = 5000,
                 read_timeout_ms: int = 500,
                 name: str = "whisker_controller",
                 sysevent_prefix: str = "sys_",
                 **kwargs) -> None:
        """
        Args:
            server: host name or IP address of Whisker server
            parent: optional parent :`QObject`
            connect_timeout_ms: time to wait for successful connection (ms)
                before considering it a failure
            read_timeout_ms: time to wait for each read (primary effect is to
                determine the application's responsivity when asked to finish;
                see :class:`WhiskerMainSocketListener`)
            name: (name for :class:`StatusMixin`)
            sysevent_prefix: default system event prefix (for
                :class:`WhiskerController`)
            kwargs: parameters to superclass
        """
        super().__init__(
            # For QObject:
            parent=parent,

            # For StatusMixin:
            name=name,
            logger=log,

            # For WhiskerApi:
            whisker_immsend_get_reply_fn=self._get_immsock_response,
            sysevent_prefix=sysevent_prefix,

            # Anyone else?
            **kwargs
        )
        self.server = server
        self.connect_timeout_ms = connect_timeout_ms
        self.read_timeout_ms = read_timeout_ms

        self.immport = None  # type: int
        self.code = None  # type: str
        self.immsocket = None  # type: QTcpSocket
        self.residual = ''

    # noinspection PyArgumentList
    @pyqtSlot(str, arrow.Arrow)
    @exit_on_exception
    def main_received(self, msg: str, timestamp: arrow.Arrow) -> None:
        """
        Slot to process a message that has come in from the main socket.

        Args:
            msg: raw message
            timestamp: server timestamp
        """
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
            # noinspection PyUnresolvedReferences
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
        elif gre.search(KEY_EVENT_REGEX, msg):
            key = gre.group(1)
            self.key_event_received.emit(key, timestamp, whisker_timestamp)
        elif gre.search(CLIENT_MESSAGE_REGEX, msg):
            source_client_num = int(gre.group(1))
            client_msg = gre.group(2)
            self.client_message_received.emit(source_client_num, client_msg,
                                              timestamp, whisker_timestamp)
        elif WARNING_REGEX.match(msg):
            self.warning_received.emit(msg, timestamp, whisker_timestamp)
        elif SYNTAX_ERROR_REGEX.match(msg):
            self.syntax_error_received.emit(msg, timestamp, whisker_timestamp)
        elif ERROR_REGEX.match(msg):
            self.error_received.emit(msg, timestamp, whisker_timestamp)
        elif msg == PING_ACK:
            self.pingack_received.emit(timestamp, whisker_timestamp)

    # noinspection PyArgumentList
    @pyqtSlot()
    @exit_on_exception
    def task_finished(self) -> None:
        """
        Slot called when the task says that it's finished.
        """
        self.debug("Task reports that it is finished")
        self._close_immsocket()
        self.finished.emit()

    def _sendline_immsock(self, *args) -> None:
        msg = msg_from_args(*args)
        self.debug("Sending to server (IMM): {}".format(msg))
        final_str = msg + EOL
        data_bytes = final_str.encode(ENCODING)
        self.immsocket.write(data_bytes)
        self.immsocket.waitForBytesWritten(INFINITE_WAIT)
        # http://doc.qt.io/qt-4.8/qabstractsocket.html
        self.immsocket.flush()

    def _getline_immsock(self) -> str:
        """
        Get one line from the socket, and returns it. Blocking.

        We must also respond to the possibility that the socket has been
        forcibly closed.
        """
        data = self.residual
        while EOL not in data and is_socket_connected(self.immsocket):
            # get more data from socket
            # self.debug("WAITING FOR DATA")
            self.immsocket.waitForReadyRead(INFINITE_WAIT)
            # self.debug("DATA READY. READING IT.")
            newdata_bytearray = self.immsocket.readAll()  # type: QByteArray
            newdata_str = newdata_bytearray.data().decode(ENCODING)
            data += newdata_str
            # self.debug("DATA: {}".format(repr(data)))
        # self.debug("DATA COMPLETE")
        if EOL in data:
            eol_index = data.index(EOL)
            line = data[:eol_index]
            self.residual = data[eol_index + EOL_LEN:]
        else:
            line = ''  # socket is closed
            self.residual = data  # probably blank!
        self.debug("Reply from server (IMM): {}".format(line))
        return line

    def _get_immsock_response(self, *args) -> Optional[str]:
        """
        Builds its arguments into a string, sends it as a command to the
        Whisker server via the immediate socket, waits for a reply, and
        returns it. (Returns ``None`` if the socket isn't connected.)
        """
        if not self.is_connected():
            self.error("Not connected")
            return None
        self._sendline_immsock(*args)
        reply = self._getline_immsock()
        return reply

    def is_connected(self) -> bool:
        """
        Is our immediate socket connected?

        (If the immediate socket is running, the main socket should be too.)
        """
        return is_socket_connected(self.immsocket)

    def _close_immsocket(self) -> None:
        """
        Close the immediate socket.
        """
        if is_socket_connected(self.immsocket):
            self.immsocket.close()

    def ping(self) -> None:
        """
        Ping the server.

        Override :func:`WhiskerApi.ping` so we can emit a signal on success.
        """
        # override WhiskerApi.ping() so we can emit a signal on success
        reply, whisker_timestamp = self._immresp_with_timestamp(PING)
        if reply == PING_ACK:
            timestamp = arrow.now()
            self.pingack_received.emit(timestamp, whisker_timestamp)


# =============================================================================
# Object from which Whisker tasks should be subclassed
# =============================================================================

class WhiskerQtTask(QObject, StatusMixin):
    """
    Base class for building a Whisker task itself. You should derive from
    this.

    - Lives in Whisker thread (B) (see :class:`WhiskerOwner`).

    Signals:

    - ``finished()``

    """
    finished = pyqtSignal()  # emit from stop() function when all done

    def __init__(self, parent: QObject = None,
                 name: str ="whisker_task", **kwargs) -> None:
        """
        Args:
            parent: optional parent :`QObject`
            name: (name for :class:`StatusMixin`)
            kwargs: parameters to superclass
        """
        super().__init__(name=name, logger=log, parent=parent, **kwargs)
        self.whisker = None

    def set_controller(self, controller: WhiskerController) -> None:
        """
        Called by :class:`WhiskerOwner`. No need to override.
        """
        self.whisker = controller

    # noinspection PyMethodMayBeStatic,PyArgumentList
    @pyqtSlot()
    def thread_started(self) -> None:
        """
        Slot called from the :func:`WhiskerOwner.taskthread.started` signal,
        which is called indirectly by :func:`WhiskerOwner.start`.

        - Use this for additional setup if required.
        - No need to override in simple situations.
        """
        pass

    # noinspection PyArgumentList
    @pyqtSlot()
    def stop(self) -> None:
        """
        Called by the :class:`WhiskerOwner` when we should stop.

        - When we've done what we need to, we should emit the ``finished``
          signal.
        - No need to override in simple situations.

        NOTE: if you think this function is not being called, the likely reason
        is not a Qt signal/slot failure, but that the thread is BUSY, e.g.
        with its immediate socket. (It'll be busy via the derived class, not
        via the code here, which does no waiting!)
        """
        self.info("WhiskerQtTask: stopping")
        self.finished.emit()

    @exit_on_exception
    def on_connect(self) -> None:
        """
        The :class:`WhiskerOwner` makes this slot get called when the
        :class:`WhiskerController` is connected.

        You should override this.
        """
        self.warning("on_connect: YOU SHOULD OVERRIDE THIS")

    # noinspection PyUnusedLocal,PyArgumentList
    @pyqtSlot(str, arrow.Arrow, int)
    @exit_on_exception
    def on_event(self, event: str, timestamp: arrow.Arrow,
                 whisker_timestamp_ms: int) -> None:
        """
        General Whisker events come here.

        Args:
            event: incoming event
            timestamp: time of receipt by client
            whisker_timestamp_ms: server's timestamp (ms)
        """
        # You should override this
        msg = "SHOULD BE OVERRIDDEN. EVENT: {}".format(event)
        self.status(msg)

    # noinspection PyUnusedLocal,PyArgumentList
    @pyqtSlot(str, arrow.Arrow, int)
    @exit_on_exception
    def on_key_event(self, key_event: str, timestamp: arrow.Arrow,
                     whisker_timestamp_ms: int) -> None:
        """
        Keyboard events come here.

        Args:
            key_event: incoming event
            timestamp: time of receipt by client
            whisker_timestamp_ms: server's timestamp (ms)
        """
        msg = "SHOULD BE OVERRIDDEN. KEY EVENT: {}".format(key_event)
        self.status(msg)

    # noinspection PyUnusedLocal,PyArgumentList
    @pyqtSlot(int, str, arrow.Arrow, int)
    @exit_on_exception
    def on_client_message(self,
                          source_client_num: int,
                          client_msg: str,
                          timestamp: arrow.Arrow,
                          whisker_timestamp_ms: int) -> None:
        """
        Client messages (from other clients) come here.

        Args:
            source_client_num: client number of sender
            client_msg: message
            timestamp: time of receipt by client
            whisker_timestamp_ms: server's timestamp (ms)
        """
        msg = "SHOULD BE OVERRIDDEN. CLIENT MESSAGE FROM CLIENT {}: {}".format(
            source_client_num, repr(client_msg))
        self.status(msg)

    # noinspection PyUnusedLocal,PyArgumentList
    @pyqtSlot(str, arrow.Arrow, int)
    @exit_on_exception
    def on_warning(self, msg: str, timestamp: arrow.Arrow,
                   whisker_timestamp_ms: int) -> None:
        """
        Warnings from the server come here.

        Args:
            msg: incoming event
            timestamp: time of receipt by client
            whisker_timestamp_ms: server's timestamp (ms)
        """
        self.warning(msg)

    # noinspection PyUnusedLocal,PyArgumentList
    @pyqtSlot(str, arrow.Arrow, int)
    @exit_on_exception
    def on_error(self, msg: str, timestamp: arrow.Arrow,
                 whisker_timestamp_ms: int) -> None:
        """
        Error reports from the server come here.

        Args:
            msg: incoming event
            timestamp: time of receipt by client
            whisker_timestamp_ms: server's timestamp (ms)
        """
        self.error(msg)

    # noinspection PyUnusedLocal,PyArgumentList
    @pyqtSlot(str, arrow.Arrow, int)
    @exit_on_exception
    def on_syntax_error(self, msg: str, timestamp: arrow.Arrow,
                        whisker_timestamp_ms: int) -> None:
        """
        Syntax error reports from the server come here.

        Args:
            msg: incoming event
            timestamp: time of receipt by client
            whisker_timestamp_ms: server's timestamp (ms)
        """
        self.error(msg)
