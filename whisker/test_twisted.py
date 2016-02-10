#!/usr/bin/env python
# whisker/test_twisted.py
# Copyright (c) Rudolf Cardinal (rudolf@pobox.com).
# See LICENSE for details.

import argparse
import logging

from twisted.internet import reactor

from whisker.constants import (
    DEFAULT_PORT,
    REPORT_NAME,
    TEST_NETWORK_LATENCY,
    TIMER_SET_EVENT,
    TIMESTAMPS,
)
from whisker.twistedclient import WhiskerTask


class MyWhiskerTask(WhiskerTask):
    def __init__(self, ):
        super().__init__()  # call base class init
        # ... anything extra here

    def fully_connected(self):
        print("SENDING SOME TEST/DEMONSTRATION COMMANDS")
        self.command(TIMESTAMPS, "on")
        self.command(REPORT_NAME, "WHISKER_CLIENT_PROTOTYPE")
        self.send(TEST_NETWORK_LATENCY)
        self.command(TIMER_SET_EVENT, "1000 9 TimerFired")
        self.command(TIMER_SET_EVENT, "12000 0 EndOfTask")

    def incoming_event(self, event, timestamp=None):
        print("Event: {e} (timestamp {t})".format(e=event, t=timestamp))
        if event == "EndOfTask":
            reactor.stop()


if __name__ == '__main__':
    logging.getLogger("whisker").setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser("Test Whisker raw socket client")
    parser.add_argument('--server', default='localhost',
                        help="Server (default: localhost)")
    parser.add_argument('--port', default=DEFAULT_PORT, type=int,
                        help="Port (default: {})".format(DEFAULT_PORT))
    args = parser.parse_args()

    print("Module run explicitly. Running a Whisker test.")
    w = MyWhiskerTask()
    w.connect(args.server, args.port)
    reactor.run()
