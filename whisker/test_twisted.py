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
    Pen,
    PenStyle,
    BrushStyle,
    BrushHatchStyle,
    Brush,
    Rectangle,
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
        self.whisker.get_network_latency_ms()
        self.whisker.report_name("Whisker Twisted client prototype")
        self.whisker.timestamps(True)
        self.whisker.timer_set_event("TimerFired", 1000, 9)
        self.whisker.timer_set_event("EndOfTask", 12000)
        DISPLAY = "display"
        DOC = "doc"
        BG_COL = (0, 0, 100)
        pen = Pen(width=3, colour=(255, 255, 150), style=PenStyle.solid)
        brush = Brush(colour=(255, 0, 0), bg_colour=(0, 255, 0),
                 opaque=True, style=BrushStyle.hatched,
                 hatch_style=BrushHatchStyle.bdiagonal)
        self.whisker.claim_display_by_num(0, alias=DISPLAY)
        self.whisker.display_create_document(DOC)
        self.whisker.display_set_background_colour(DOC, BG_COL)
        self.whisker.display_show_document(DISPLAY, DOC)
        self.whisker.display_add_obj_text(
            DOC, "_text", (50, 50), "hello there!",
            italic=True)
        self.whisker.display_add_obj_line(
            DOC, "_line", (25, 25), (200, 200), pen)
        self.whisker.display_add_obj_arc(
            DOC, "_arc",
            Rectangle(left=100, top=100, width=200, height=200),
            (25, 25), (200, 200), pen)
        self.whisker.display_add_obj_bezier(
            DOC, "_bezier",
            (100, 100), (150, 100),
            (150, 200), (100, 200),
            pen)
        self.whisker.display_add_obj_chord(
            DOC, "_chord",
            Rectangle(left=300, top=0, width=100, height=100),
            (100, 150), (400, 175),
            pen, brush)
        self.whisker.display_add_obj_ellipse(
            DOC, "_ellipse",
            Rectangle(left=0, top=200, width=200, height=100),
            pen, brush)
        self.whisker.display_add_obj_pie(
            DOC, "_pie",
            Rectangle(left=0, top=300, width=200, height=100),
            (10, 320), (180, 380),
            pen, brush)
        self.whisker.display_add_obj_polygon(
            DOC, "_polygon",
            [(400, 200), (450, 300), (400, 400), (300, 300)],
            pen, brush, alternate=True)
        self.whisker.display_add_obj_rectangle(
            DOC, "_rectangle",
            Rectangle(left=500, top=0, width=200, height=100),
            pen, brush)
        self.whisker.display_add_obj_roundrect(
            DOC, "_roundrect",
            Rectangle(left=500, top=200, width=100, height=200),
            150, 250,
            pen, brush)
        self.whisker.display_add_obj_camcogquadpattern(
            DOC, "_camcogquad",
            (500, 400),
            10, 10,
            [1, 2, 4, 8, 16, 32, 64, 128],
            [255, 254, 253, 252, 251, 250, 249, 248],
            [1, 2, 3, 4, 5, 6, 7, 8],
            [128, 64, 32, 16, 8, 4, 2, 1],
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (255, 0, 255),
            (100, 100, 100))
        self.whisker.display_set_event(DOC, "_camcogquad", "quad_touched")

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
