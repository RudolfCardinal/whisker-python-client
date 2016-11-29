#!/usr/bin/env python
# whisker/logging.py
# Copyright (c) Rudolf Cardinal (rudolf@pobox.com).
# See LICENSE for details.

from html import escape
import json
import logging
from typing import Any, Callable, Dict, Optional

from colorlog import ColoredFormatter

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

# =============================================================================
# Constants
# =============================================================================


LOG_FORMAT = '%(asctime)s.%(msecs)03d:%(levelname)s:%(name)s:%(message)s'
COLOUR_LOG_FORMAT = (
    "%(cyan)s%(asctime)s.%(msecs)03d %(name)s:%(levelname)s: "
    "%(log_color)s%(message)s"
)
LOG_DATEFMT = '%Y-%m-%d %H:%M:%S'

LOG_COLORS = {
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'red,bg_white',
}
COLOUR_FORMATTER = ColoredFormatter(
    COLOUR_LOG_FORMAT,
    datefmt=LOG_DATEFMT,
    reset=True,
    log_colors=LOG_COLORS,
    secondary_log_colors={},
    style='%'
)
COLOUR_HANDLER = logging.StreamHandler()
COLOUR_HANDLER.setLevel(logging.DEBUG)
COLOUR_HANDLER.setFormatter(COLOUR_FORMATTER)


# =============================================================================
# Helper functions
# =============================================================================

def configure_logger_for_colour(log: logging.Logger,
                                remove_existing: bool = True) -> None:
    """
    Applies a preconfigured datetime/colour scheme to a logger.
    Should ONLY be called from the "if __name__ == 'main'" script:
        https://docs.python.org/3.4/howto/logging.html#library-config
    """
    if remove_existing:
        log.handlers = []  # http://stackoverflow.com/questions/7484454
    log.addHandler(COLOUR_HANDLER)


def configure_all_loggers_for_colour(remove_existing: bool = True) -> None:
    """
    Applies a preconfigured datetime/colour scheme to ALL logger.
    Should ONLY be called from the "if __name__ == 'main'" script:
        https://docs.python.org/3.4/howto/logging.html#library-config
    Generally MORE SENSIBLE just to apply a handler to the root logger.
    """
    apply_handler_to_all_logs(COLOUR_HANDLER, remove_existing=remove_existing)


def apply_handler_to_root_log(handler: logging.Handler,
                              remove_existing: bool = False) -> None:
    """
    Applies a handler to all logs, optionally removing existing handlers.
    Should ONLY be called from the "if __name__ == 'main'" script:
        https://docs.python.org/3.4/howto/logging.html#library-config
    Generally MORE SENSIBLE just to apply a handler to the root logger.
    """
    rootlog = logging.getLogger()
    if remove_existing:
        rootlog.handlers = []
    rootlog.addHandler(handler)


def apply_handler_to_all_logs(handler: logging.Handler,
                              remove_existing: bool = False) -> None:
    """
    Applies a handler to all logs, optionally removing existing handlers.
    Should ONLY be called from the "if __name__ == 'main'" script:
        https://docs.python.org/3.4/howto/logging.html#library-config
    Generally MORE SENSIBLE just to apply a handler to the root logger.
    """
    # noinspection PyUnresolvedReferences
    for name, obj in logging.Logger.manager.loggerDict.items():
        if remove_existing:
            obj.handlers = []  # http://stackoverflow.com/questions/7484454
        obj.addHandler(handler)


def copy_root_log_to_file(filename: str,
                          fmt: str = LOG_FORMAT,
                          datefmt: str = LOG_DATEFMT) -> None:
    """
    Copy all currently configured logs to the specified file.
    Should ONLY be called from the "if __name__ == 'main'" script:
        https://docs.python.org/3.4/howto/logging.html#library-config
    """
    fh = logging.FileHandler(filename)
    # default file mode is 'a' for append
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
    fh.setFormatter(formatter)
    apply_handler_to_root_log(fh)


def copy_all_logs_to_file(filename: str,
                          fmt: str = LOG_FORMAT,
                          datefmt: str = LOG_DATEFMT) -> None:
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


# noinspection PyProtectedMember
def get_formatter_report(f: logging.Formatter) -> Optional[Dict[str, str]]:
    """Returns information on a log formatter, as a dictionary.
    For debugging."""
    if f is None:
        return None
    return {
        '_fmt': f._fmt,
        'datefmt': f.datefmt,
        '_style': str(f._style),
    }


def get_handler_report(h: logging.Handler) -> Dict[str, Any]:
    """Returns information on a log handler, as a dictionary. For debugging."""
    return {
        'get_name()': h.get_name(),
        'level': h.level,
        'formatter': get_formatter_report(h.formatter),
        'filters': h.filters,
    }


def get_log_report(log: logging.Logger) -> Dict[str, Any]:
    """Returns information on a log, as a dictionary. For debugging."""
    # suppress invalid error for Logger.manager:
    # noinspection PyUnresolvedReferences
    return {
        '(object)': str(log),
        'level': log.level,
        'disabled': log.disabled,
        'propagate': log.propagate,
        'parent': str(log.parent),
        'manager': str(log.manager),
        'handlers': [get_handler_report(h) for h in log.handlers],
    }


def print_report_on_all_logs() -> None:
    """
    Use print() to report information on all logs.
    """
    d = {}
    # noinspection PyUnresolvedReferences
    for name, obj in logging.Logger.manager.loggerDict.items():
        d[name] = get_log_report(obj)
    d['(root logger)'] = get_log_report(logging.getLogger())
    print(json.dumps(d, sort_keys=True, indent=4, separators=(',', ': ')))


# =============================================================================
# HTML formatter
# =============================================================================

class HtmlColorFormatter(logging.Formatter):
    log_colors = {
        logging.DEBUG: '#008B8B',  # dark cyan
        logging.INFO: '#00FF00',  # green
        logging.WARNING: '#FFFF00',  # yellow
        logging.ERROR: '#FF0000',  # red
        logging.CRITICAL: '#FF0000',  # red
    }
    log_background_colors = {
        logging.DEBUG: None,
        logging.INFO: None,
        logging.WARNING: None,
        logging.ERROR: None,
        logging.CRITICAL: '#FFFFFF',  # white
    }

    def __init__(self, append_br: bool = False,
                 replace_nl_with_br: bool = True) -> None:
        # https://hg.python.org/cpython/file/3.5/Lib/logging/__init__.py
        super().__init__(
            fmt='%(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            style='%'
        )
        self.append_br = append_br
        self.replace_nl_with_br = replace_nl_with_br

    def format(self, record: logging.LogRecord) -> str:
        # record is a LogRecord
        # https://docs.python.org/3.4/library/logging.html#logging.LogRecord

        # message = super().format(record)
        super().format(record)
        # Since fmt does not contain asctime, the Formatter.format()
        # will not write asctime (since its usesTime()) function will be
        # false. Therefore:
        record.asctime = self.formatTime(record, self.datefmt)
        bg_col = self.log_background_colors[record.levelno]
        msg = escape(record.getMessage())
        # escape() won't replace \n but will replace & etc.
        if self.replace_nl_with_br:
            msg = msg.replace("\n", "<br>")
        html = (
            '<span style="color:#008B8B">{time}.{ms:03d} {name}:{lvname}: '
            '</span><span style="color:{color}{bg}">{msg}</font>{br}'.format(
                time=record.asctime,
                ms=int(record.msecs),
                name=record.name,
                lvname=record.levelname,
                color=self.log_colors[record.levelno],
                msg=msg,
                bg=";background-color:{}".format(bg_col) if bg_col else "",
                br="<br>" if self.append_br else "",
            )
        )
        # print("record.__dict__: {}".format(record.__dict__))
        # print("html: {}".format(html))
        return html


# =============================================================================
# HTML handler (using HtmlColorFormatter) that sends output to a function,
# e.g. for display in a Qt window
# =============================================================================

class HtmlColorHandler(logging.StreamHandler):
    def __init__(self, logfunction: Callable[[str], None],
                 level: int = logging.INFO) -> None:
        super().__init__()
        self.logfunction = logfunction
        self.setFormatter(HtmlColorFormatter())
        self.setLevel(level)

    def emit(self, record: logging.LogRecord) -> None:
        # noinspection PyBroadException
        try:
            html = self.format(record)
            self.logfunction(html)
        except:
            self.handleError(record)
