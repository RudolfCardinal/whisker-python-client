#!/usr/bin/env python
# whisker/interface.py
# Copyright (c) Rudolf Cardinal (rudolf@pobox.com).
# See LICENSE for details.

import re


def split_terminal_timestamp(msg):
    try:
        m = re.match("(.*)\s+\[(\w+)\]$", msg)
        mainmsg = m.group(1)
        timestamp = int(m.group(2))
        return (mainmsg, timestamp)
    except:
        return (msg, None)


def on_off_to_boolean(msg):
    return True if msg == "on" else False
