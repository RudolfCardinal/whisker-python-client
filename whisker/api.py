#!/usr/bin/env python
# whisker/api.py

from .callback import CallbackHandler
from .constants import (
    CMD_LINE_SET_STATE,
    CMD_TIMER_SET_EVENT,
    VAL_ON,
    VAL_OFF,
)


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
        n_called = self.callback_handler.process_event(event)
        return n_called > 0 or event.startswith(self.sysevent_prefix)

    def send_after_delay(self, delay_ms, msg, event=''):
        event = event or self.get_new_sysevent("send", msg)
        self.timer_set_event(event, delay_ms)
        self.callback_handler.add_single(event, self._immsend, msg)

    def call_after_delay(self, delay_ms, callback, *args, event='', **kwargs):
        event = event or self.get_new_sysevent("call")
        self.timer_set_event(event, delay_ms)
        self.callback_handler.add_single(event, callback, *args, **kwargs)

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
                              line, not on_now, timing_sequence, event=event)

    # -------------------------------------------------------------------------
    # Whisker command set
    # -------------------------------------------------------------------------

    def timer_set_event(self, event, duration_ms, reload_count=0):
        self._immsend(CMD_TIMER_SET_EVENT, duration_ms, reload_count, event)

    def line_set_state(self, line, on):
        self._immsend(CMD_LINE_SET_STATE, line, VAL_ON if on else VAL_OFF)

    # -------------------------------------------------------------------------
    # Shortcuts to Whisker commands
    # -------------------------------------------------------------------------

    def line_on(self, line):
        self.line_set_state(line, True)

    def line_off(self, line):
        self.line_set_state(line, False)
