#!/usr/bin/env python
# whisker/logging.py
# Copyright (c) Rudolf Cardinal (rudolf@pobox.com).
# See LICENSE for details.

import colorlog
import json
import logging

"""
See https://docs.python.org/3.4/howto/logging.html#library-config

USER CODE should use the following general methods.

(a) Simple:

    import logging
    log = logging.getLogger(__name__)  # for your own logs
    logging.basicConfig()

(b) More complex:

    import logging
    log = logging.getLogger(__name__)
    logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATEFMT,
                        level=loglevel)

(c) Using colour conveniently:

    import logging
    mylogger = logging.getLogger(__name__)
    rootlogger = logging.getLogger()

    from whisker.log import configure_logger_for_colour
    configure_logger_for_colour(rootlogger)


LIBRARY CODE should use the following general methods.

    import logging
    log = logging.getLogger(__name__)

    # ... and if you want to suppress output unless the user configures logs:
    log.addHandler(logging.NullHandler())
    # ... which only needs to be done in the __init__.py for the package
    #     http://stackoverflow.com/questions/12296214

    # LIBRARY CODE SHOULD NOT ADD ANY OTHER HANDLERS; see above.

"""


LOG_FORMAT = '%(asctime)s.%(msecs)03d:%(levelname)s:%(name)s:%(message)s'
COLOUR_LOG_FORMAT = (
    "%(cyan)s%(asctime)s.%(msecs)03d %(name)s:%(levelname)s: "
    "%(log_color)s%(message)s"
)
LOG_DATEFMT = '%Y-%m-%d %H:%M:%S'

COLOUR_FORMATTER = colorlog.ColoredFormatter(
    COLOUR_LOG_FORMAT,
    datefmt=LOG_DATEFMT,
    reset=True,
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    },
    secondary_log_colors={},
    style='%'
)
COLOUR_HANDLER = logging.StreamHandler()
COLOUR_HANDLER.setLevel(logging.DEBUG)
COLOUR_HANDLER.setFormatter(COLOUR_FORMATTER)


def configure_logger_for_colour(log, remove_existing=True):
    """
    Applies a preconfigured datetime/colour scheme to a logger.
    Should ONLY be called from the "if __name__ == 'main'" script:
        https://docs.python.org/3.4/howto/logging.html#library-config
    """
    if remove_existing:
        log.handlers = []  # http://stackoverflow.com/questions/7484454
    log.addHandler(COLOUR_HANDLER)


def configure_all_loggers_for_colour(remove_existing=True):
    """
    Applies a preconfigured datetime/colour scheme to ALL logger.
    Should ONLY be called from the "if __name__ == 'main'" script:
        https://docs.python.org/3.4/howto/logging.html#library-config
    Generally MORE SENSIBLE just to apply a handler to the root logger.
    """
    apply_handler_to_all_logs(COLOUR_HANDLER, remove_existing=remove_existing)


def apply_handler_to_all_logs(handler, remove_existing=False):
    """
    Applies a handler to all logs, optionally removing existing handlers.
    Should ONLY be called from the "if __name__ == 'main'" script:
        https://docs.python.org/3.4/howto/logging.html#library-config
    Generally MORE SENSIBLE just to apply a handler to the root logger.
    """
    for name, obj in logging.Logger.manager.loggerDict.items():
        if remove_existing:
            obj.handlers = []  # http://stackoverflow.com/questions/7484454
        obj.addHandler(handler)


def copy_all_logs_to_file(filename, fmt=LOG_FORMAT, datefmt=LOG_DATEFMT):
    """
    Copy all currently configured logs to the specified file.
    Should ONLY be called from the "if __name__ == 'main'" script:
        https://docs.python.org/3.4/howto/logging.html#library-config
    """
    fh = logging.FileHandler(filename)
    # default file mode is 'a' for append
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
    fh.setFormatter(formatter)
    apply_handler_to_all_logs(fh)


def get_formatter_report(f):
    """Returns information on a log formatter, as a dictionary.
    For debugging."""
    if f is None:
        return None
    return {
        '_fmt': f._fmt,
        'datefmt': f.datefmt,
        '_style': str(f._style),
    }


def get_handler_report(h):
    """Returns information on a log handler, as a dictionary. For debugging."""
    return {
        'get_name()': h.get_name(),
        'level': h.level,
        'formatter': get_formatter_report(h.formatter),
        'filters': h.filters,
    }


def get_log_report(log):
    """Returns information on a log, as a dictionary. For debugging."""
    return {
        '(object)': str(log),
        'level': log.level,
        'disabled': log.disabled,
        'propagate': log.propagate,
        'parent': str(log.parent),
        'manager': str(log.manager),
        'handlers': [get_handler_report(h) for h in log.handlers],
    }


def print_report_on_all_logs():
    """
    Use print() to report information on all logs.
    """
    d = {}
    for name, obj in logging.Logger.manager.loggerDict.items():
        d[name] = get_log_report(obj)
    d['(root logger)'] = get_log_report(logging.getLogger())
    print(json.dumps(d, sort_keys=True, indent=4, separators=(',', ': ')))
