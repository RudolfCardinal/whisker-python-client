#!/usr/bin/env python
# whisker/callback.py

import logging
log = logging.getLogger(__name__)


# =============================================================================
# Event callback handler. Distinct from any particular network/threading
# model, so all can use it.
# =============================================================================

class CallbackDefinition(object):
    def __init__(self, event, callback, args, kwargs, target_n_calls=0,
                 swallow_event=False):
        self.event = event
        self.callback = callback
        self.args = args or []
        self.kwargs = kwargs or {}
        self.target_n_calls = target_n_calls
        self.swallow_event = swallow_event
        self.n_calls = 0

    def __repr__(self):
        return (
            "CallbackDefinition(event={}, callback={}, args={}, "
            "kwargs={}, target_n_calls={}, n_calls={}".format(
                self.event, repr(self.callback), repr(self.args),
                repr(self.kwargs), self.target_n_calls, self.n_calls,
            )
        )

    def call(self):
        self.n_calls += 1
        log.debug(
            "Callback #{n_calls} to {func}, args={args}, "
            "kwargs={kwargs}".format(
                n_calls=self.n_calls,
                func=self.callback.__name__,
                args=self.args,
                kwargs=self.kwargs,
            )
        )
        self.callback(*self.args, **self.kwargs)

    def is_defunct(self):
        return self.target_n_calls > 0 and self.n_calls >= self.target_n_calls


class CallbackHandler(object):
    """
    Implements callbacks based on Whisker events.
    """

    def __init__(self):
        self.callbacks = []  # list of WhiskerCallbackDefinition objects

    def add(self, target_n_calls, event, callback, args=None, kwargs=None,
            swallow_event=True):
        """Adds a callback."""
        swallow_event = kwargs.pop('swallow_event', True)
        cd = CallbackDefinition(event, callback, args, kwargs,
                                target_n_calls=target_n_calls,
                                swallow_event=swallow_event)
        self.callbacks.append(cd)

    def add_single(self, event, callback, args=None, kwargs=None,
                   swallow_event=True):
        """Adds a single-shot callback."""
        self.add(1, event, callback, args, kwargs)

    def add_persistent(self, event, callback, args=None, kwargs=None,
                       swallow_event=True):
        """Adds a persistent callback."""
        self.add(0, event, callback, args, kwargs)

    def remove(self, event, callback=None):
        """Removes a callback (either by event/callback pair, or all callbacks
        for an event."""
        self.callbacks = [
            x for x in self.callbacks
            if not (x.event == event and (callback is None or
                                          x.callback == callback))]

    def clear(self):
        """Removes all callbacks."""
        self.callbacks = []

    def process_event(self, event):
        """Calls any callbacks for the event. Returns the number of callbacks
        called."""
        n_called = 0
        swallow_event = False
        for x in self.callbacks:
            if x.event == event:
                x.call()
                swallow_event = swallow_event or x.swallow_event
        # Remove any single-shot callbacks
        self.callbacks = [x for x in self.callbacks if not x.is_defunct()]
        return n_called, swallow_event

    def debug(self):
        """Write debugging information to the log."""
        log.debug("CallbackHandler: callbacks are...")
        for c in self.callbacks:
            log.debug(repr(c))
        log.debug("... end of CallbackHandler calls")
