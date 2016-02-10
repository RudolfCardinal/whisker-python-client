#!/usr/bin/env python3
# whisker/convenience.py

import logging
from datetime import datetime
from tkinter import filedialog, Tk
import sys

from attrdict import AttrDict
import colorama
from colorama import Fore, Back, Style
import dataset
import yaml

from .colourlog import configure_logger_for_colour

logger = logging.getLogger(__name__)
configure_logger_for_colour(logger)
colorama.init()


def load_config_or_die():
    """Offers a GUI file prompt; loads a YAML config from it; or exits."""
    Tk().withdraw()  # we don't want a full GUI; remove root window
    config_filename = filedialog.askopenfilename(
        title='Open configuration file',
        filetypes=[('YAML files', '.yaml'), ('All files', '*.*')])
    if not config_filename:
        logger.critical("No config file given; exiting.")
        sys.exit(1)
    logger.info("Loading config from: {}".format(config_filename))
    with open(config_filename) as infile:
        return AttrDict(yaml.safe_load(infile))


def connect_to_db_using_attrdict(database_url, show_url=False):
    """Connects to a dataset database, and uses AttrDict as the row type, so
    AttrDict objects come back out again."""
    if show_url:
        logger.info("Connecting to database: {}".format(database_url))
    else:
        logger.info("Connecting to database")
    return dataset.connect(database_url, row_type=AttrDict)



def ask_user(prompt, default=None, type=str, min=None, max=None,
             allow_none=True):
    """Prompts the user, with a default. Coerces the return type"""
    defstr = ""
    minmaxstr = ""
    if default is not None:
        type(default)  # will raise if the user has passed a dumb default
        defstr = " [{}]".format(str(default))
    if min is not None or max is not None:
        minmaxstr = " ({}–{})".format(
            min if min is not None else '',
            max if max is not None else '')
    prompt = "{c}{p}{m}{d}: {r}".format(
        c=Fore.YELLOW + Style.BRIGHT,
        p=prompt,
        m=minmaxstr,
        d=defstr,
        r=Style.RESET_ALL,
    )
    while True:
        try:
            str_answer = input(prompt) or default
            value = type(str_answer) if str_answer is not None else None
            if value is None and not allow_none:
                raise ValueError()
            if ((min is not None and value < min) or
                    (max is not None and value > max)):
                raise ValueError()
            return value
        except:
            print("Bad input value; try again.")


def save_data(tablename, results, taskname, timestamp=None,
              output_format="csv"):
    """
    Saves a dataset result set to a suitable output file.
    output_format can be one of: csv, json, tabson
        (see https://dataset.readthedocs.org/en/latest/api.html#dataset.freeze)
    """
    if timestamp is None:
        timestamp = datetime.utcnow()
    filename = "{taskname}_{datetime}.{tablename}.{output_format}".format(
        taskname=taskname,
        tablename=tablename,
        datetime=timestamp.isoformat(),
        output_format=output_format
    )
    logger.info("Saving {tablename} data to {filename}".format(
        tablename=tablename, filename=filename))
    dataset.freeze(results, format=output_format, filename=filename)


def insert_and_set_id(table, object, idfield='id'):
    """The dataset table's insert() command returns the primary key.
    However, it doesn't store that back, and we want users to do that
    consistently."""
    pk = table.insert(object)
    object[idfield] = pk
    return pk
