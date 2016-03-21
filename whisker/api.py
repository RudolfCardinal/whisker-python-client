#!/usr/bin/env python
# whisker/api.py

import logging
import re

from whisker.callback import CallbackHandler

log = logging.getLogger(__name__)

# =============================================================================
# API constants
# =============================================================================

# -----------------------------------------------------------------------------
# Interface basics
# -----------------------------------------------------------------------------

EOL = '\n'
# Whisker sends (and accepts) LF between responses, and we are operating in the
# str (not bytes) domain; see below re readAll().
EOL_LEN = len(EOL)

# -----------------------------------------------------------------------------
# Server -> client
# -----------------------------------------------------------------------------

IMMPORT_REGEX = re.compile(r"^ImmPort: (\d+)")
CODE_REGEX = re.compile(r"^Code: (\w+)")
TIMESTAMP_REGEX = re.compile(r"^(.*)\s+\[(\d+)\]$")

RESPONSE_SUCCESS = "Success"
RESPONSE_FAILURE = "Failure"
PING = "Ping"
PING_ACK = "PingAcknowledged"

EVENT_REGEX = re.compile(r"^Event: (.*)$")
KEY_EVENT_REGEX = re.compile(r"^KeyEvent: (.*)$")
CLIENT_MESSAGE_REGEX = re.compile(r"^ClientMessage: (.*)$")
INFO_REGEX = re.compile(r"^Info: (.*)$")
WARNING_REGEX = re.compile(r"Warning: (.*)$")
SYNTAX_ERROR_REGEX = re.compile(r"^SyntaxError: (.*)$")
ERROR_REGEX = re.compile(r"Error: (.*)$")

EVENT_PREFIX = "Event: "
KEY_EVENT_PREFIX = "KeyEvent: "
CLIENT_MESSAGE_PREFIX = "ClientMessage: "
INFO_PREFIX = "Info: "
WARNING_PREFIX = "Warning: "
SYNTAX_ERROR_PREFIX = "SyntaxError: "
ERROR_PREFIX = "Error: "

# -----------------------------------------------------------------------------
# Client -> server
# -----------------------------------------------------------------------------

CMD_TEST_NETWORK_LATENCY = "TestNetworkLatency"
CMD_WHISKER_STATUS = "WhiskerStatus"
CMD_REPORT_NAME = "ReportName"
CMD_TIMESTAMPS = "Timestamps"

CMD_TIMER_SET_EVENT = "TimerSetEvent"
CMD_TIMER_CLEAR_EVENT = "TimerClearEvent"
CMD_TIMER_CLEAR_ALL_EVENTS = "TimerClearAllEvents"

CMD_CLAIM_GROUP = "ClaimGroup"
CMD_LINE_CLEAR_ALL_EVENTS = "LineClearAllEvents"
CMD_LINE_CLAIM = "LineClaim"
CMD_LINE_SET_STATE = "LineSetState"
CMD_LINE_SET_EVENT = "LineSetEvent"

FLAG_INPUT = "-input"
FLAG_OUTPUT = "-output"

VAL_ON = "on"
VAL_OFF = "off"
VAL_BOTH = "both"

# *** more to do


# =============================================================================
# Helper functions
# =============================================================================

def _on_val(on):
    return VAL_ON if on else VAL_OFF


def split_terminal_timestamp(msg):
    try:
        m = TIMESTAMP_REGEX.match(msg)
        mainmsg = m.group(1)
        timestamp = int(m.group(2))
        return (mainmsg, timestamp)
    except:
        return (msg, None)


def on_off_to_boolean(msg):
    return True if msg == "on" else False


def s_to_ms(time_seconds):
    return int(time_seconds * 1000)


def min_to_ms(time_minutes):
    return int(time_minutes * 60000)


# =============================================================================
# API handler. Distinct from any particular network/threading
# model, so all can use it (e.g. by inheritance), but hooks in to whichever
# you choose.
# =============================================================================

class WhiskerApi(object):
    def __init__(self, whisker_immsend_fn, sysevent_prefix="sys_"):
        self._immsend = whisker_immsend_fn
        self.sysevent_prefix = sysevent_prefix
        self.sysevent_counter = 0
        self.callback_handler = CallbackHandler()

    # -------------------------------------------------------------------------
    # Custom event handling, e.g. for line flashing
    # -------------------------------------------------------------------------

    def get_new_sysevent(self, *args):
        self.sysevent_counter += 1
        return self.sysevent_prefix + "_".join(
            str(x) for x in [self.sysevent_counter] + list(args)
        ).replace(" ", "")

    def process_backend_event(self, event):
        """Returns True if the backend API has dealt with the event and it
        doesn't need to go to the main behavioural task."""
        n_called, swallow_event = self.callback_handler.process_event(event)
        return (
            (n_called > 0 and swallow_event) or
            event.startswith(self.sysevent_prefix)
        )

    def send_after_delay(self, delay_ms, msg, event=''):
        event = event or self.get_new_sysevent("send", msg)
        self.timer_set_event(event, delay_ms)
        self.callback_handler.add_single(event, self._immsend, msg)

    def call_after_delay(self, delay_ms, callback, args=None, kwargs=None,
                         event=''):
        args = args or []
        kwargs = kwargs or {}
        event = event or self.get_new_sysevent("call")
        self.timer_set_event(event, delay_ms)
        self.callback_handler.add_single(event, callback, args, kwargs)

    def call_on_event(self, event, callback, args=None, kwargs=None,
                      swallow_event=False):
        args = args or []
        kwargs = kwargs or {}
        self.callback_handler.add_persistent(event, callback, args, kwargs,
                                             swallow_event=swallow_event)

    def clear_event_callback(self, event, callback=None):
        self.callback_handler.remove(event, callback=callback)

    def clear_all_callbacks(self):
        self.callback_handler.clear()

    def debug_callbacks(self):
        self.callback_handler.debug()

    def flash_line_pulses(self, line, count, on_ms, off_ms, on_at_rest=False):
        assert count > 0
        # Generally better to ping-pong the events, rather than line them up
        # in advance, in case the user specifies very rapid oscillation that
        # exceeds the network bandwidth, or something; better to be slow than
        # to garbage up the sequence.
        if on_at_rest:
            # Currently at rest = on.
            # For 4 flashes:
            # OFF .. ON .... OFF .. ON .... OFF .. ON .... OFF .. ON
            on_now = False
            timing_sequence = [off_ms] + (count - 1) * [on_ms, off_ms]
        else:
            # Currently at rest = off.
            # For 4 flashes:
            # ON .... OFF .. ON .... OFF .. ON .... OFF .. ON .... OFF
            on_now = True
            timing_sequence = [on_ms] + (count - 1) * [off_ms, on_ms]
        total_duration_ms = sum(timing_sequence)
        self.flash_line_ping_pong(line, on_now, timing_sequence)
        return total_duration_ms

    def flash_line_ping_pong(self, line, on_now, timing_sequence):
        """
        line: line number/name
        on_now: switch it on or off now?
        timing_sequence: array of times (in ms) for the next things
        """
        self.line_on(line) if on_now else self.line_off(line)
        if not timing_sequence:
            return
        delay_ms = timing_sequence[0]
        timing_sequence = timing_sequence[1:]
        event = self.get_new_sysevent(line, "off" if on_now else "on")
        self.call_after_delay(delay_ms, self.flash_line_ping_pong,
                              args=[line, not on_now, timing_sequence],
                              event=event)

    # -------------------------------------------------------------------------
    # Whisker command set: timers
    # -------------------------------------------------------------------------

    def timer_set_event(self, event, duration_ms, reload_count=0):
        self._immsend(CMD_TIMER_SET_EVENT, duration_ms, reload_count, event)

    def timer_clear_event(self, event):
        self._immsend(CMD_TIMER_CLEAR_EVENT, event)

    def timer_clear_all_events(self):
        self._immsend(CMD_TIMER_CLEAR_ALL_EVENTS)

    # -------------------------------------------------------------------------
    # Whisker command set: lines
    # -------------------------------------------------------------------------

    def line_set_state(self, line, on):
        self._immsend(CMD_LINE_SET_STATE, line, _on_val(on))

    def line_set_event(self, line, event, on=True, off=False):
        if on and off:
            transition = VAL_BOTH
        elif on:
            transition = VAL_ON
        elif off:
            transition = VAL_OFF
        else:
            log.warn("line_set_event called with on=False, off=False")
            return
        self._immsend(CMD_LINE_SET_EVENT, line, transition, event)

    def line_clear_all_events(self):
        self._immsend(CMD_LINE_CLEAR_ALL_EVENTS)

    # -------------------------------------------------------------------------
    # Whisker command set: comms
    # -------------------------------------------------------------------------

    def timestamps(self, on):
        self._immsend(CMD_TIMESTAMPS, _on_val(on))

    # -------------------------------------------------------------------------
    # Shortcuts to Whisker commands
    # -------------------------------------------------------------------------

    def line_on(self, line):
        self.line_set_state(line, True)

    def line_off(self, line):
        self.line_set_state(line, False)


# *** more to do
