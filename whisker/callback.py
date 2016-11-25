#!/usr/bin/env python
# whisker/callback.py

import logging
from typing import Any, Callable, Dict, List, Tuple

log = logging.getLogger(__name__)


# =============================================================================
# Event callback handler. Distinct from any particular network/threading
# model, so all can use it.
# =============================================================================

class CallbackDefinition(object):
    def __init__(self,
                 event: str,
                 callback: Callable[..., Any],
                 args: List[Any] = None,
                 kwargs: Dict[str, Any] = None,
                 target_n_calls: int = 0,
                 swallow_event: bool = False) -> None:
        self.event = event
        self.callback = callback
        self.args = args or []  # type: List[Any]
        self.kwargs = kwargs or {}  # type: Dict[str, Any]
        self.target_n_calls = target_n_calls
        self.swallow_event = swallow_event
        self.n_calls = 0

    def __repr__(self) -> str:
        return (
            "CallbackDefinition(event={}, callback={}, args={}, "
            "kwargs={}, target_n_calls={}, n_calls={}".format(
                self.event, repr(self.callback), repr(self.args),
                repr(self.kwargs), self.target_n_calls, self.n_calls,
            )
        )

    def call(self) -> None:
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

    def is_defunct(self) -> bool:
        return 0 < self.target_n_calls <= self.n_calls


class CallbackHandler(object):
    """
    Implements callbacks based on Whisker events.
    """

    def __init__(self) -> None:
        self.callbacks = []  # list of WhiskerCallbackDefinition objects

    def add(self,
            target_n_calls: int,
            event: str,
            callback: Callable[..., Any],
            args: List[Any] = None,
            kwargs: Dict[str, Any] = None,
            swallow_event: bool = True) -> None:
        """Adds a callback."""
        cd = CallbackDefinition(event, callback, args, kwargs,
                                target_n_calls=target_n_calls,
                                swallow_event=swallow_event)
        self.callbacks.append(cd)

    def add_single(self,
                   event: str,
                   callback: Callable[..., Any],
                   args: List[Any] = None,
                   kwargs: Dict[str, Any] = None,
                   swallow_event: bool = True) -> None:
        """Adds a single-shot callback."""
        self.add(1, event, callback, args, kwargs, swallow_event=swallow_event)

    def add_persistent(self,
                       event: str,
                       callback: Callable[..., Any],
                       args: List[Any] = None,
                       kwargs: Dict[str, Any] = None,
                       swallow_event: bool = True) -> None:
        """Adds a persistent callback."""
        self.add(0, event, callback, args, kwargs, swallow_event=swallow_event)

    def remove(self, event: str, callback: Callable[..., None] = None) -> None:
        """Removes a callback (either by event/callback pair, or all callbacks
        for an event."""
        self.callbacks = [
            x for x in self.callbacks
            if not (x.event == event and (callback is None or
                                          x.callback == callback))]

    def clear(self) -> None:
        """Removes all callbacks."""
        self.callbacks = []

    def process_event(self, event: str) -> Tuple[int, bool]:
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

    def debug(self) -> None:
        """Write debugging information to the log."""
        log.debug("CallbackHandler: callbacks are...")
        for c in self.callbacks:
            log.debug(repr(c))
        log.debug("... end of CallbackHandler calls")
