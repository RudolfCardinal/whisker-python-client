#!/usr/bin/env python
# whisker/test_rawsockets.py

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

**Command-line tool to test the Whisker raw-socket client.**

"""

import argparse
import logging

from cardinal_pythonlib.logs import configure_logger_for_colour
from whisker.api import (
    EVENT_PREFIX,
    PING_ACK,
    CMD_REPORT_NAME,
    CMD_TEST_NETWORK_LATENCY,
    CMD_TIMER_SET_EVENT,
    CMD_WHISKER_STATUS,
)
from whisker.constants import DEFAULT_PORT
from whisker.rawsocketclient import WhiskerRawSocketClient


def test_whisker(server: str,
                 port: int = DEFAULT_PORT,
                 verbose_network: bool = True) -> None:
    """
    Tests the Whisker raw-socket client.

    Args:
        server: Whisker server IP address or hostname
        port: main Whisker port number
        verbose_network: be verbose about network traffic
    """
    w = WhiskerRawSocketClient()
    print("Connecting to {}:{}".format(server, port))
    if not w.connect_both_ports(server, port):
        raise RuntimeError("Failed to connect")

    w.send(CMD_REPORT_NAME + " Whisker python demo program")
    w.send(CMD_WHISKER_STATUS)
    reply = w.send_immediate(CMD_TIMER_SET_EVENT + " 1000 9 TimerFired")
    print("... reply to TimerSetEvent was: {}".format(reply))
    reply = w.send_immediate(CMD_TIMER_SET_EVENT + " 12000 0 EndOfTask")
    print("... reply to TimerSetEvent was: {}".format(reply))
    w.send(CMD_TEST_NETWORK_LATENCY)

    for line in w.getlines_mainsock():
        if verbose_network:
            print("SERVER: " + line)  # For info only.
        if line == "Ping":
            # If the server has sent us a Ping, acknowledge it.
            w.send(PING_ACK)
        if line[:7] == EVENT_PREFIX:
            # The server has sent us an event.
            event = line[7:]
            if verbose_network:
                print("EVENT RECEIVED: " + event)  # For info only.
            # Event handling for the behavioural task is dealt with here.
            if event == "EndOfTask":
                break  # Exit the for loop.


def main() -> None:
    """
    Command-line parser.
    See ``--help`` for details.
    """
    logging.basicConfig()
    logging.getLogger("whisker").setLevel(logging.DEBUG)
    configure_logger_for_colour(logging.getLogger())  # configure root logger

    parser = argparse.ArgumentParser("Test Whisker raw socket client")
    parser.add_argument('--server', default='localhost',
                        help="Server (default: localhost)")
    parser.add_argument('--port', default=DEFAULT_PORT, type=int,
                        help="Port (default: {})".format(DEFAULT_PORT))
    args = parser.parse_args()

    test_whisker(server=args.server, port=args.port)


if __name__ == '__main__':
    main()
