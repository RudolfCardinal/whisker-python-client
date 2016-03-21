#!/usr/bin/env python
# whisker/twistedclient.py
# Copyright (c) Rudolf Cardinal (rudolf@pobox.com).
# See LICENSE for details.

"""
Event-driven framework for Whisker Python clients using Twisted.

Author: Rudolf Cardinal (rudolf@pobox.com)
Created: 18 Aug 2011
Last update: 10 Feb 2016
"""

import logging
import re
import socket

from twisted.internet import reactor
# from twisted.internet.stdio import StandardIO
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import LineReceiver

from whisker.api import (
    CLIENT_MESSAGE_PREFIX,
    ERROR_PREFIX,
    EVENT_PREFIX,
    INFO_PREFIX,
    KEY_EVENT_PREFIX,
    SYNTAX_ERROR_PREFIX,
    WARNING_PREFIX,
    split_terminal_timestamp,
    on_off_to_boolean,
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

class WhiskerTask(object):
    """Usage: see test_twisted.py."""

    def __init__(self):
        self.server = None
        self.mainport = None
        self.immport = None
        self.code = None
        self.mainsocket = None
        self.immsocket = None
        self.mainfactory = WhiskerMainPortFactory(self)

    @classmethod
    def set_verbose_logging(cls, verbose):
        if verbose:
            log.setLevel(logging.DEBUG)
        else:
            log.setLevel(logging.INFO)

    def connect(self, server, port):
        self.server = server
        self.mainport = get_port(port)
        log.info(
            "Attempting to connect to Whisker server {s} on port {p}".format(
                s=self.server,
                p=self.mainport
            ))
        reactor.connectTCP(self.server, self.mainport, self.mainfactory)

    def connect_immediate(self):
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

    def fully_connected(self):
        """Override this."""
        pass

    def send(self, msg):
        if not self.mainsocket:
            log.error("can't send without a mainsocket")
            return
        self.mainsocket.send(msg)

    def send_and_get_reply(self, msg):
        if not self.immsocket:
            log.error("can't send_and_get_reply without an immsocket")
            return
        reply = self.immsocket.send_and_get_reply(msg)
        return reply

    def command(self, *args):
        return self.send_and_get_reply(" ".join([str(x) for x in args]))

    def incoming_message(self, msg):
        log.debug("INCOMING MESSAGE: " + str(msg))
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
            self.connect_immediate()
        if handled:
            return

        (msg, timestamp) = split_terminal_timestamp(msg)

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

        log.debug("Unhandled incoming_message: " + str(msg))

    def incoming_event(self, event, timestamp=None):
        """Override this."""
        log.debug("UNHANDLED EVENT: {e} (timestamp={t}".format(
            e=event,
            t=timestamp
        ))

    def incoming_client_message(self, fromclientnum, msg, timestamp=None):
        """Override this."""
        log.debug(
            "UNHANDLED CLIENT MESSAGE from client {c}: {m} "
            "(timestamp={t})".format(
                c=fromclientnum,
                m=msg,
                t=timestamp
            ))

    def incoming_key_event(self, key, depressed, document, timestamp=None):
        """Override this."""
        log.debug(
            "UNHANDLED KEY EVENT: key {k} {dr} (document={d}, "
            "timestamp={t})".format(
                k=key,
                dr="depressed" if depressed else "released",
                d=document,
                t=timestamp
            ))

    def incoming_info(self, msg):
        """Override this."""
        log.debug(msg)

    def incoming_warning(self, msg):
        """Override this."""
        log.debug(msg)

    def incoming_error(self, msg):
        """Override this."""
        log.debug(msg)

    def incoming_syntax_error(self, msg):
        """Override this."""
        log.debug(msg)


class WhiskerMainPortFactory(ClientFactory):

    def __init__(self, task):
        self.task = task

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        log.warning("WhiskerMainPortFactory: disconnected")
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        log.error("connection failed: " + str(reason))
        reactor.stop()

    def buildProtocol(self, addr):
        log.debug("WhiskerMainPortFactory: buildProtocol({})".format(addr))
        if self.task.mainsocket:
            log.error("mainsocket already connected")
            return None
        p = WhiskerMainPortProtocol(self.task)
        return p


class WhiskerMainPortProtocol(LineReceiver):

    delimiter = b"\n"  # MUST BE BYTES, NOT STR!
    # Otherwise, you get a crash ('str' does not support the buffer interface)
    # from within twisted/protocols/basic.py, line 559, when it tries to do
    #   something = bytes_buffer.split(string_delimiter, 1)

    def __init__(self, task, encoding='ascii'):
        self.task = task
        self.task.mainsocket = self
        self.encoding = encoding

    def connectionMade(self):
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

    def lineReceived(self, data):
        str_data = data.decode(self.encoding)
        log.debug("Main port received: {}".format(str_data))
        self.task.incoming_message(str_data)

    def send(self, data):
        log.debug("Main port sending: {}".format(data))
        self.sendLine(data.encode(self.encoding))


class WhiskerImmSocket(object):
    """Uses raw sockets."""

    def __init__(self, task):
        self.task = task
        self.connected = False
        self.error = ""
        self.immsock = None

    def connect(self, server, port):
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

    def getlines_immsock(self):
        """Yield a set of lines from the socket."""
        log.debug("WhiskerImmSocket: getlines_immsock")
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
                    buf = buf + more
        if buf:
            yield buf

    def send_and_get_reply(self, msg):
        log.debug("Immediate socket sending: " + msg)
        socket_sendall(self.immsock, msg + "\n")
        reply = next(self.getlines_immsock())
        log.debug("Immediate socket reply: " + reply)
        return reply
