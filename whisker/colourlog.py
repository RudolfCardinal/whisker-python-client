#!/usr/bin/env python3
# whisker/configure_colour_console_log.py

import colorlog
import logging

colour_formatter = colorlog.ColoredFormatter(
    "%(asctime)s.%(msecs)03d %(cyan)s%(name)s:%(levelname)s: "
    "%(log_color)s%(message)s",
    datefmt='%Y-%m-%d %H:%M:%S',
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
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(colour_formatter)


def configure_logger_for_colour(logger, level=logging.DEBUG):
    """Applies a preconfigured datetime/colour scheme to a logger."""
    logger.addHandler(ch)
    logger.setLevel(level)
