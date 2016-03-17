#!/usr/bin/env python
# whisker/test_twisted.py
# Copyright (c) Rudolf Cardinal (rudolf@pobox.com).
# See LICENSE for details.

import argparse
import logging

from twisted.internet import reactor

from whisker.api import (
    CMD_REPORT_NAME,
    CMD_TEST_NETWORK_LATENCY,
    CMD_TIMER_SET_EVENT,
    CMD_TIMESTAMPS,
)
from whisker.constants import DEFAULT_PORT
from whisker.logging import (
    configure_logger_for_colour,
    # print_report_on_all_logs,
)
from whisker.twistedclient import WhiskerTask


class MyWhiskerTask(WhiskerTask):
    def __init__(self, ):
        super().__init__()  # call base class init
        # ... anything extra here

    def fully_connected(self):
        print("SENDING SOME TEST/DEMONSTRATION COMMANDS")
        self.command(CMD_TIMESTAMPS, "on")
        self.command(CMD_REPORT_NAME, "WHISKER_CLIENT_PROTOTYPE")
        self.send(CMD_TEST_NETWORK_LATENCY)
        self.command(CMD_TIMER_SET_EVENT, "1000 9 TimerFired")
        self.command(CMD_TIMER_SET_EVENT, "12000 0 EndOfTask")

    def incoming_event(self, event, timestamp=None):
        print("Event: {e} (timestamp {t})".format(e=event, t=timestamp))
        if event == "EndOfTask":
            reactor.stop()


def main():
    logging.basicConfig()
    logging.getLogger("whisker").setLevel(logging.DEBUG)
    configure_logger_for_colour(logging.getLogger())  # configure root logger
    # print_report_on_all_logs()

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


if __name__ == '__main__':
    main()
