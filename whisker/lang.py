#!/usr/bin/env python
# starfeeder/lang.py
# Copyright (c) Rudolf Cardinal (rudolf@pobox.com).
# See LICENSE for details.

from collections import Counter, OrderedDict
from functools import total_ordering
import inspect
import logging
import os
import re
import subprocess
import sys
import types
from typing import (Any, Dict, Iterable, List, Match, Optional, Pattern,
                    TextIO, Union)

log = logging.getLogger(__name__)


# =============================================================================
# Natural sorting, e.g. for COM ports
# =============================================================================
# http://stackoverflow.com/questions/5967500/how-to-correctly-sort-a-string-with-a-number-inside  # noqa

def atoi(text: str) -> Union[int, str]:
    return int(text) if text.isdigit() else text


def natural_keys(text) -> List[Union[int, str]]:
    return [atoi(c) for c in re.split('(\d+)', text)]


# =============================================================================
# Dictionaries, lists
# =============================================================================

def reversedict(d: Dict[Any, Any]) -> Dict[Any, Any]:
    return {v: k for k, v in d.items()}


def contains_duplicates(values: Iterable[Any]) -> bool:
    for v in Counter(values).values():
        if v > 1:
            return True
    return False


def sort_list_by_index_list(x: List[Any], indexes: List[int]) -> None:
    """Re-orders x by the list of indexes of x, in place."""
    x[:] = [x[i] for i in indexes]


def flatten_list(x: List[Any]) -> List[Any]:
    return [item for sublist in x for item in sublist]
    # http://stackoverflow.com/questions/952914/making-a-flat-list-out-of-list-of-lists-in-python  # noqa


# =============================================================================
# Number printing, e.g. for parity
# =============================================================================

def trunc_if_integer(n: Any) -> Any:
    if n == int(n):
        return int(n)
    return n


# =============================================================================
# File output
# =============================================================================

def writeline_nl(fileobj: TextIO, line: str) -> None:
    fileobj.write(line + '\n')


def writelines_nl(fileobj: TextIO, lines: Iterable[str]) -> None:
    # Since fileobj.writelines() doesn't add newlines...
    # http://stackoverflow.com/questions/13730107/writelines-writes-lines-without-newline-just-fills-the-file  # noqa
    fileobj.write('\n'.join(lines) + '\n')


# =============================================================================
# Class to store last match of compiled regex
# =============================================================================
# Based on http://stackoverflow.com/questions/597476/how-to-concisely-cascade-through-multiple-regex-statements-in-python  # noqa

class CompiledRegexMemory(object):
    def __init__(self) -> None:
        self.last_match = None

    def match(self, compiled_regex: Pattern, text: str) -> Match:
        self.last_match = compiled_regex.match(text)
        return self.last_match

    def search(self, compiled_regex: Pattern, text: str) -> Match:
        self.last_match = compiled_regex.search(text)
        return self.last_match

    def group(self, n: int) -> Optional[str]:
        if not self.last_match:
            return None
        return self.last_match.group(n)


# =============================================================================
# Name of calling class/function, for status messages
# =============================================================================

def get_class_from_frame(fr: types.FrameType) -> Optional[str]:
    # http://stackoverflow.com/questions/2203424/python-how-to-retrieve-class-information-from-a-frame-object  # noqa
    args, _, _, value_dict = inspect.getargvalues(fr)
    # we check the first parameter for the frame function is named 'self'
    if len(args) and args[0] == 'self':
        # in that case, 'self' will be referenced in value_dict
        instance = value_dict.get('self', None)
        if instance:
            # return its class
            cls = getattr(instance, '__class__', None)
            if cls:
                return cls.__name__
            return None
    # return None otherwise
    return None


# noinspection PyProtectedMember
def get_caller_name(back: int = 0) -> str:
    """
    Return details about the CALLER OF THE CALLER (plus n calls further back)
    of this function.
    """
    # http://stackoverflow.com/questions/5067604/determine-function-name-from-within-that-function-without-using-traceback  # noqa
    try:
        frame = sys._getframe(back + 2)
    except ValueError:
        # Stack isn't deep enough.
        return '?'
    function_name = frame.f_code.co_name
    class_name = get_class_from_frame(frame)
    if class_name:
        return "{}.{}".format(class_name, function_name)
    return function_name


# =============================================================================
# AttrDict classes
# =============================================================================

# attrdict itself: use the attrdict package

class OrderedNamespace(object):
    # http://stackoverflow.com/questions/455059
    # ... modified for init
    def __init__(self, *args):
        super().__setattr__('_odict', OrderedDict(*args))

    def __getattr__(self, key):
        odict = super().__getattribute__('_odict')
        if key in odict:
            return odict[key]
        return super().__getattribute__(key)

    def __setattr__(self, key, val):
        self._odict[key] = val

    @property
    def __dict__(self):
        return self._odict

    def __setstate__(self, state):  # Support copy.copy
        super().__setattr__('_odict', OrderedDict())
        self._odict.update(state)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self.__eq__(other)

    # Plus more (RNC):
    def items(self):
        return self.__dict__.items()

    def __repr__(self):
        return ordered_repr(self, self.__dict__.keys())


# =============================================================================
# repr assistance function
# =============================================================================

def ordered_repr(obj: object, attrlist: Iterable[str]) -> str:
    """
    Shortcut to make repr() functions ordered.
    Define your repr like this:

        def __repr__(self):
            return ordered_repr(self, ["field1", "field2", "field3"])
    """
    return "<{classname}({kvp})>".format(
        classname=type(obj).__name__,
        kvp=", ".join("{}={}".format(a, repr(getattr(obj, a)))
                      for a in attrlist)
    )


def simple_repr(obj: object) -> str:
    """Even simpler."""
    return "<{classname}({kvp})>".format(
        classname=type(obj).__name__,
        kvp=", ".join("{}={}".format(k, repr(v))
                      for k, v in obj.__dict__.items())
    )


# =============================================================================
# Launch external file using OS's launcher
# =============================================================================

def launch_external_file(filename: str) -> None:
    if sys.platform.startswith('linux'):
        subprocess.call(["xdg-open", filename])
    else:
        # noinspection PyUnresolvedReferences
        os.startfile(filename)


# =============================================================================
# Sorting
# =============================================================================

@total_ordering
class MinType(object):
    """Compares less than anything else."""
    def __le__(self, other: Any) -> bool:
        return True

    def __eq__(self, other: Any) -> bool:
        return self is other


mintype_singleton = MinType()


# noinspection PyPep8Naming
class attrgetter_nonesort:
    """
    Modification of operator.attrgetter
    Returns an object's attributes, or the mintype_singleton if the attribute
    is None.
    """
    __slots__ = ('_attrs', '_call')

    def __init__(self, attr, *attrs):
        if not attrs:
            if not isinstance(attr, str):
                raise TypeError('attribute name must be a string')
            self._attrs = (attr,)
            names = attr.split('.')

            def func(obj):
                for name in names:
                    obj = getattr(obj, name)
                if obj is None:  # MODIFIED HERE
                    return mintype_singleton
                return obj

            self._call = func
        else:
            self._attrs = (attr,) + attrs
            # MODIFIED HERE:
            getters = tuple(map(attrgetter_nonesort, self._attrs))

            def func(obj):
                return tuple(getter(obj) for getter in getters)

            self._call = func

    def __call__(self, obj):
        return self._call(obj)

    def __repr__(self):
        return '%s.%s(%s)' % (self.__class__.__module__,
                              self.__class__.__qualname__,
                              ', '.join(map(repr, self._attrs)))

    def __reduce__(self):
        return self.__class__, self._attrs


# noinspection PyPep8Naming
class methodcaller_nonesort:
    """
    As above, but for methodcaller.
    """
    __slots__ = ('_name', '_args', '_kwargs')

    def __init__(*args, **kwargs):
        if len(args) < 2:
            msg = "methodcaller needs at least one argument, the method name"
            raise TypeError(msg)
        self = args[0]
        self._name = args[1]
        if not isinstance(self._name, str):
            raise TypeError('method name must be a string')
        self._args = args[2:]
        self._kwargs = kwargs

    def __call__(self, obj):
        # MODIFICATION HERE
        result = getattr(obj, self._name)(*self._args, **self._kwargs)
        if result is None:
            return mintype_singleton
        return result

    def __repr__(self):
        args = [repr(self._name)]
        args.extend(map(repr, self._args))
        args.extend('%s=%r' % (k, v) for k, v in self._kwargs.items())
        return '%s.%s(%s)' % (self.__class__.__module__,
                              self.__class__.__name__,
                              ', '.join(args))

    def __reduce__(self):
        if not self._kwargs:
            return self.__class__, (self._name,) + self._args
        else:
            from functools import partial
            return (
                partial(self.__class__, self._name, **self._kwargs),
                self._args
            )
