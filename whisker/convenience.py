#!/usr/bin/env python
# whisker/convenience.py

"""
===============================================================================

    Copyright (C) 2011-2018 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of the Whisker Python client library.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

===============================================================================

**Convenience functions for simple Whisker clients.**

"""

import logging
from datetime import datetime
from tkinter import filedialog, Tk
import os
import sys
from typing import Any, Dict, Iterable, List, Type, Union

import arrow
from attrdict import AttrDict
import colorama
from colorama import Fore, Style
import dataset
# noinspection PyPackageRequirements
import yaml  # from pyyaml

from whisker.constants import FILENAME_SAFE_ISOFORMAT

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
colorama.init()


def load_config_or_die(mandatory: Iterable[Union[str, List[Any]]] = None,
                       defaults: Dict[str, Any] = None,
                       log_config: bool = False) -> AttrDict:
    """
    Offers a GUI file prompt; loads a YAML config from it; or exits.

    Args:
        mandatory: list of mandatory items;
            if one of these is itself a list, that list is used as a hierarchy
            of attributes
        defaults: a dict-like object of defaults
        log_config: report the config to the Python log?

    Returns:
        an class:`AttrDict` containing the config

    """
    def _fail_mandatory(attrname_):
        errmsg = "Setting '{}' missing from config file".format(attrname_)
        log.critical(errmsg)
        sys.exit(1)

    mandatory = mandatory or []  # type: List[str]
    defaults = defaults or {}  # type: Dict[str, Any]
    defaults = AttrDict(defaults)
    Tk().withdraw()  # we don't want a full GUI; remove root window
    config_filename = filedialog.askopenfilename(
        title='Open configuration file',
        filetypes=[('YAML files', '.yaml'), ('All files', '*.*')])
    if not config_filename:
        log.critical("No config file given; exiting.")
        sys.exit(1)
    log.info("Loading config from: {}".format(config_filename))
    with open(config_filename) as infile:
        config = AttrDict(yaml.safe_load(infile))
    for attr in mandatory:
        if len(attr) > 1 and not isinstance(attr, str):
            # attr is a list of attributes, e.g. ['a', 'b', 'c'] for a.b.c
            obj = config
            so_far = []
            for attrname in attr:
                so_far.append(attrname)
                if attrname not in obj:
                    _fail_mandatory(".".join(so_far))
                obj = obj[attrname]
        else:
            # attr is a string
            if attr not in config:
                _fail_mandatory(attr)
    config = defaults + config  # use AttrDict to update
    if log_config:
        log.debug("config: {}".format(repr(config)))
    return config


def connect_to_db_using_attrdict(database_url: str,
                                 show_url: bool = False,
                                 engine_kwargs: Dict[str, Any] = None):
    """
    Connects to a ``dataset`` database, and uses :class:`AttrDict` as the row
    type, so :class:`AttrDict` objects come back out again.
    """
    if show_url:
        log.info("Connecting to database: {}".format(database_url))
    else:
        log.info("Connecting to database")
    return dataset.connect(database_url, row_type=AttrDict,
                           engine_kwargs=engine_kwargs)


# noinspection PyShadowingBuiltins
def ask_user(prompt: str,
             default: Any = None,
             type: Type[Any] = str,
             min: Any = None,
             max: Any = None,
             options: List[Any] = None,
             allow_none: bool = True) -> Any:
    """
    Prompts the user via the command line, optionally with a default, range or
    set of options. Asks for user input. Coerces the return type.

    Args:
        prompt: prompt to display
        default: default value if the user just presses Enter
        type: type to coerce return value to (default ``str``)
        min: if not ``None``, enforce this minimum value
        max: if not ``None``, enforce this maximum value
        options: permitted options (if this is truthy and the user enters an
            option that's not among then, raise :exc:`ValueError`)
        allow_none: permit the return of ``None`` values (otherwise, if a
            ``None`` value would be returned, raise :exc:`ValueError`)

    Returns:
        user-supplied value

    """
    options = options or []
    defstr = ""
    minmaxstr = ""
    optionstr = ""
    if default is not None:
        type(default)  # will raise if the user has passed a dumb default
        defstr = " [{}]".format(str(default))
    if min is not None or max is not None:
        minmaxstr = " ({} to {})".format(
            min if min is not None else '–∞',
            max if max is not None else '+∞')
    if options:
        optionstr = " {{{}}}".format(", ".join(str(x) for x in options))
        for o in options:
            type(o)  # will raise if the user has passed a dumb option
    prompt = "{c}{p}{m}{o}{d}: {r}".format(
        c=Fore.YELLOW + Style.BRIGHT,
        p=prompt,
        m=minmaxstr,
        o=optionstr,
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
            if options and value not in options:
                raise ValueError()
            return value
        except (TypeError, ValueError):
            print("Bad input value; try again.")


def save_data(tablename: str,
              results: List[Dict[str, Any]],
              taskname: str,
              timestamp: Union[arrow.Arrow, datetime] = None,
              output_format: str = "csv") -> None:
    """
    Saves a ``dataset`` result set to a suitable output file.

    Args:
        tablename: table name, used only for creating the filename
        results: results to save
        taskname: task name, used only for creating the filename
        timestamp: timestamp, used only for creating the filename; if ``None``,
            the current date/time is used
        output_format: one of: ``"csv"``, ``"json"``, ``"tabson"``
            (see
            https://dataset.readthedocs.org/en/latest/api.html#dataset.freeze)
    """
    if timestamp is None:
        timestamp = datetime.utcnow()
    filename = "{taskname}_{datetime}_{tablename}.{output_format}".format(
        taskname=taskname,
        tablename=tablename,
        datetime=timestamp.strftime(FILENAME_SAFE_ISOFORMAT),
        output_format=output_format
    )
    log.info("Saving {tablename} data to {filename}".format(
        tablename=tablename, filename=filename))
    dataset.freeze(results, format=output_format, filename=filename)
    if not os.path.isfile(filename):
        log.error(
            "save_data: file {} not created; empty results?".format(filename))


def insert_and_set_id(table: dataset.Table,
                      obj: Dict[str, Any],
                      idfield: str = 'id') -> Any:  # but typically int
    """
    Inserts an object into a :class:`dataset.Table` and ensures that the
    primary key (PK) is written back to the object, in its ``idfield``.

    (The :func:`dataset.Table.insert` command returns the primary key.
    However, it doesn't store that back, and we want users to do that
    consistently.)
    """
    pk = table.insert(obj)
    obj[idfield] = pk
    return pk
