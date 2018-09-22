#!/usr/bin/env python
# whisker/twistedclient.py

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

**Event-driven framework for Whisker Python clients using Twisted.**

- Created: 18 Aug 2011
- Last update: 10 Feb 2016
"""

import logging
import re
import socket
from typing import Generator, Optional, Union

from twisted.internet import reactor
# from twisted.internet.stdio import StandardIO
from twisted.internet.protocol import ClientFactory
from twisted.internet.tcp import Connector  # for type hints
from twisted.protocols.basic import LineReceiver

from whisker.api import (
    CLIENT_MESSAGE_PREFIX,
    ERROR_PREFIX,
    EVENT_PREFIX,
    INFO_PREFIX,
    KEY_EVENT_PREFIX,
    msg_from_args,
    on_off_to_boolean,
    split_timestamp,
    SYNTAX_ERROR_PREFIX,
    WARNING_PREFIX,
    WhiskerApi,
)
from whisker.socket import (
    get_port,
    socket_receive,
    socket_sendall,
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# =============================================================================
# Event-driven Whisker task class. Use this one.
# =============================================================================

class WhiskerTwistedTask(object):
    """
    Base class for Whisker clients using the Twisted socket system.

    - Contains ``self.whisker``, an instance of
      :class:`whisker.api.WhiskerApi`.
    - Specimen usage: see ``test_twisted.py``.
    """

    def __init__(self) -> None:
        self.server = None
        self.mainport = None
        self.immport = None
        self.code = None
        self.mainsocket = None
        self.immsocket = None
        self.mainfactory = WhiskerMainPortFactory(self)
        self.whisker = WhiskerApi(
            whisker_immsend_get_reply_fn=self.send_and_get_reply)

    @classmethod
    def set_verbose_logging(cls, verbose: bool) -> None:
        """
        Sets the Python log level for this module.

        Args:
            verbose: be verbose?
        """
        if verbose:
            log.setLevel(logging.DEBUG)
        else:
            log.setLevel(logging.INFO)

    def connect(self, server: str, port: Union[str, int]) -> None:
        """
        Connects to the Whisker server.

        Args:
            server: Whisker server hostname/IP address
            port: Whisker main TCP/IP port number
        """
        self.server = server
        self.mainport = get_port(port)
        log.info(
            "Attempting to connect to Whisker server {s} on port {p}".format(
                s=self.server,
                p=self.mainport
            ))
        # noinspection PyUnresolvedReferences
        reactor.connectTCP(self.server, self.mainport, self.mainfactory)

    def _connect_immediate(self) -> None:
        """
        Connect the Whisker immediate socket.
        """
        # Twisted really hates blocking.
        # So we need to do some special things here.
        self.immsocket = WhiskerImmSocket(self)
        log.info(
            "Attempting to connect to Whisker server {s} on immediate "
            "port {p}".format(
                s=self.server,
                p=self.immport
            ))
        self.immsocket.connect(self.server, self.immport)
        if not self.immsocket.connected:
            log.error("ERROR creating/connecting immediate socket: " +
                      str(self.immsocket.error))
        log.info("Connected to immediate port " + str(self.immport) +
                 " on server " + self.server)
        self.immsocket.send_and_get_reply("Link " + self.code)
        log.info("Server fully connected.")
        self.fully_connected()

        # sleeptime = 0.1
        # log.info("Sleeping for " + str(sleeptime) +
        #                  " seconds as the Nagle-disabling feature of Python "
        #                  "isn't working properly...")
        # time.sleep(sleeptime)
        # The Nagle business isn't working; the Link packet is getting
        # amalgamated with anything the main calling program starts to send.
        # So pause.

    def fully_connected(self) -> None:
        """
        The Whisker server is now fully connected.

        Override this, e.g. to start the task.
        """
        pass

    def send(self, *args) -> None:
        """
        Builds its arguments into a string and sends that as a command to the
        Whisker server via the main socket.
        """
        if not self.mainsocket:
            log.error("can't send without a mainsocket")
            return
        msg = msg_from_args(*args)
        self.mainsocket.send(msg)

    def send_and_get_reply(self, *args) -> Optional[str]:
        """
        Builds its arguments into a string, sends that as a command to the
        Whisker server via the immediate socket, blocks and waits for the
        reply, and returns that reply. (Returns ``None`` if not connected.)
        """
        if not self.immsocket:
            log.error("can't send_and_get_reply without an immsocket")
            return
        reply = self.immsocket.send_and_get_reply(*args)
        return reply

    def incoming_message(self, msg: str) -> None:
        """
        Processes an incoming message from the Whisker server (via the main
        socket).
        """
        # log.debug("INCOMING MESSAGE: " + str(msg))
        handled = False
        if not self.immport:
            m = re.search(r"^ImmPort: (\d+)", msg)
            if m:
                self.immport = get_port(m.group(1))
                handled = True
        if not self.code:
            m = re.search(r"^Code: (\w+)", msg)
            if m:
                self.code = m.group(1)
                handled = True
        if (not self.immsocket) and (self.immport and self.code):
            self._connect_immediate()
        if handled:
            return

        (msg, timestamp) = split_timestamp(msg)

        if msg == "Ping":
            # If the server has sent us a Ping, acknowledge it.
            self.send("PingAcknowledged")
            return

        if msg.startswith(EVENT_PREFIX):
            # The server has sent us an event.
            event = msg[len(EVENT_PREFIX):]
            self.incoming_event(event, timestamp)
            return

        if msg.startswith(KEY_EVENT_PREFIX):
            kmsg = msg[len(KEY_EVENT_PREFIX):]
            # key on|off document
            m = re.match(r"(\w+)\s+(\w+)\s+(\w+)", kmsg)
            if m:
                key = m.group(1)
                depressed = on_off_to_boolean(m.group(2))
                document = m.group(3)
                self.incoming_key_event(key, depressed, document, timestamp)
            return

        if msg.startswith(CLIENT_MESSAGE_PREFIX):
            cmsg = msg[len(CLIENT_MESSAGE_PREFIX):]
            # fromclientnum message
            m = re.match(r"(\w+)\s+(.+)", cmsg)
            if m:
                try:
                    fromclientnum = int(m.group(1))
                    clientmsg = m.group(2)
                    self.incoming_client_message(fromclientnum, clientmsg,
                                                 timestamp)
                except (TypeError, ValueError):
                    pass
            return

        if msg.startswith(INFO_PREFIX):
            self.incoming_info(msg)
            return

        if msg.startswith(WARNING_PREFIX):
            self.incoming_warning(msg)
            return

        if msg.startswith(SYNTAX_ERROR_PREFIX):
            self.incoming_syntax_error(msg)
            return

        if msg.startswith(ERROR_PREFIX):
            self.incoming_error(msg)
            return

        log.debug("Unhandled incoming message: " + str(msg))

    def incoming_event(self, event: str, timestamp: int = None) -> None:
        """
        General Whisker event received.

        Override this function.

        Args:
            event: event
            timestamp: server timestamp (ms)
        """
        log.debug("UNHANDLED EVENT: {e} (timestamp={t}".format(
            e=event,
            t=timestamp
        ))

    # noinspection PyMethodMayBeStatic
    def incoming_client_message(self, fromclientnum: int, msg: str,
                                timestamp: int = None) -> None:
        """
        Client message (from another client) received.

        Override this function.

        Args:
            fromclientnum: source client number
            msg: message
            timestamp: server timestamp (ms)
        """
        log.debug(
            "UNHANDLED CLIENT MESSAGE from client {c}: {m} "
            "(timestamp={t})".format(
                c=fromclientnum,
                m=msg,
                t=timestamp
            ))

    # noinspection PyMethodMayBeStatic
    def incoming_key_event(self, key: str, depressed: bool, document: str,
                           timestamp: int = None) -> None:
        """
        Keyboard event received.

        Override this function.

        Args:
            key: which key?
            depressed: was it depressed (or released)?
            document: source display document
            timestamp: server timestamp (ms)
        """
        log.debug(
            "UNHANDLED KEY EVENT: key {k} {dr} (document={d}, "
            "timestamp={t})".format(
                k=key,
                dr="depressed" if depressed else "released",
                d=document,
                t=timestamp
            ))

    # noinspection PyMethodMayBeStatic
    def incoming_info(self, msg: str) -> None:
        """
        Information message received from Whisker server.

        Args:
            msg: message
        """
        log.info(msg)

    # noinspection PyMethodMayBeStatic
    def incoming_warning(self, msg: str) -> None:
        """
        Warning received from Whisker server.

        Args:
            msg: message
        """
        log.warning(msg)

    # noinspection PyMethodMayBeStatic
    def incoming_error(self, msg: str) -> None:
        """
        Error report received from Whisker server.

        Args:
            msg: message
        """
        log.error(msg)

    # noinspection PyMethodMayBeStatic
    def incoming_syntax_error(self, msg: str) -> None:
        """
        Syntax error report received from Whisker server.

        Args:
            msg: message
        """
        log.error(msg)


class WhiskerMainPortFactory(ClientFactory):
    """
    A Protocol factory for the Whisker main port.
    """

    def __init__(self, task: WhiskerTwistedTask) -> None:
        """
        Args:
            task: instance of :class:`WhiskerTwistedTask`
        """
        self.task = task

    def clientConnectionLost(self, connector: Connector, reason: str) -> None:
        """
        If we get disconnected, reconnect to server.
        """
        log.warning("WhiskerMainPortFactory: disconnected")
        connector.connect()

    def clientConnectionFailed(self, connector: Connector,
                               reason: str) -> None:
        """
        Client connection failed. Stop the reactor.
        """
        log.error("connection failed: " + str(reason))
        reactor.stop()

    def buildProtocol(self, addr: str) -> Optional['WhiskerMainPortProtocol']:
        """
        Build and return the protocol.
        """
        log.debug("WhiskerMainPortFactory: buildProtocol({})".format(addr))
        if self.task.mainsocket:
            log.error("mainsocket already connected")
            return None
        p = WhiskerMainPortProtocol(self.task)
        return p


class WhiskerMainPortProtocol(LineReceiver):
    """
    Line-based Twisted protocol for the Whisker main port.
    """

    delimiter = b"\n"  # MUST BE BYTES, NOT STR!
    # Otherwise, you get a crash ('str' does not support the buffer interface)
    # from within twisted/protocols/basic.py, line 559, when it tries to do
    #   something = bytes_buffer.split(string_delimiter, 1)

    def __init__(self, task: WhiskerTwistedTask,
                 encoding: str = 'ascii') -> None:
        """
        Args:
            task: instance of :class:`WhiskerTwistedTask`
            encoding: encoding to use; normally ``"ascii"``
        """
        self.task = task
        self.task.mainsocket = self
        self.encoding = encoding

    def connectionMade(self) -> None:
        """
        Called when the main port is connected.
        """
        peer = self.transport.getPeer()
        if hasattr(peer, "host") and hasattr(peer, "port"):
            log.info("Connected to main port {p} on server {h}".format(
                h=peer.host,
                p=peer.port
            ))
        else:
            log.debug("Connected to main port")
        self.transport.setTcpNoDelay(True)  # disable Nagle algorithm
        log.debug("Main port: Nagle algorithm disabled (TCP_NODELAY set)")

    def lineReceived(self, data: bytes) -> None:
        """
        Called when data is received on the main port.
        Sends it to :func:`WhiskerTwistedTask.incoming_message` via
        ``self.task``.

        Args:
            data: bytes
        """
        str_data = data.decode(self.encoding)
        log.debug("Main port received: {}".format(str_data))
        self.task.incoming_message(str_data)

    def send(self, data: str) -> None:
        """
        Encodes and sends data to the main port.
        """
        log.debug("Main port sending: {}".format(data))
        self.sendLine(data.encode(self.encoding))

    def rawDataReceived(self, data: bytes) -> None:
        """
        Raw data received. Unused; we use :func:`lineReceived` instead.
        """
        pass


class WhiskerImmSocket(object):
    """
    Whisker Twisted immediate socket handler.

    Uses raw sockets.
    """

    def __init__(self, task: WhiskerTwistedTask) -> None:
        """
        Args:
            task: instance of :class:`WhiskerTwistedTask`
        """
        self.task = task
        self.connected = False
        self.error = ""
        self.immsock = None

    def connect(self, server: str, port: int) -> None:
        """
        Connects the Whisker immediate socket.

        Args:
            server: server hostname/IP address
            port: immediate port number
        """
        log.debug("WhiskerImmSocket: connect")
        proto = socket.getprotobyname("tcp")
        try:
            self.immsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM,
                                         proto)
            self.immsock.connect((server, port))
            self.connected = True
        except socket.error as x:
            self.immsock.close()
            self.immsock = None
            self.error = str(x)
            return

        # Disable the Nagle algorithm:
        self.immsock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        log.debug("Immediate port: Nagle algorithm disabled (TCP_NODELAY set)")
        # Set blocking
        self.immsock.setblocking(True)
        log.debug("Immediate port: set to blocking mode")

    def getlines_immsock(self) -> Generator[str, None, None]:
        """
        Generates lines from the immediate socket.

        Yields:
            lines from the socket
        """
        # log.debug("WhiskerImmSocket: getlines_immsock")
        # http://stackoverflow.com/questions/822001/python-sockets-buffering
        buf = socket_receive(self.immsock)
        done = False
        while not done:
            if "\n" in buf:
                (line, buf) = buf.split("\n", 1)
                yield line
            else:
                more = socket_receive(self.immsock)
                if not more:
                    done = True
                else:
                    buf += more
        if buf:
            yield buf

    def send_and_get_reply(self, *args) -> str:
        """
        Builds its arguments into a string; sends it to Whisker via the
        immediate socket; gets the reply; returns it.
        """
        msg = msg_from_args(*args)
        log.debug("Immediate socket sending: " + msg)
        socket_sendall(self.immsock, msg + "\n")
        reply = next(self.getlines_immsock())
        log.debug("Immediate socket reply: " + reply)
        return reply
