#!/usr/bin/env python
# starfeeder/lang.py
# Copyright (c) Rudolf Cardinal (rudolf@pobox.com).
# See LICENSE for details.

from collections import Counter, OrderedDict
from functools import total_ordering
import inspect
import logging
log = logging.getLogger(__name__)
import operator
import os
import random
import re
import subprocess
import sys


# =============================================================================
# Natural sorting, e.g. for COM ports
# =============================================================================
# http://stackoverflow.com/questions/5967500/how-to-correctly-sort-a-string-with-a-number-inside  # noqa

def atoi(text):
    return int(text) if text.isdigit() else text


def natural_keys(text):
    return [atoi(c) for c in re.split('(\d+)', text)]


# =============================================================================
# Dictionaries, lists
# =============================================================================

def reversedict(d):
    return {v: k for k, v in d.items()}


def contains_duplicates(values):
    return [k for k, v in Counter(values).items() if v > 1]


def sort_list_by_index_list(x, indexes):
    """Re-orders x by the list of indexes of x, in place."""
    x[:] = [x[i] for i in indexes]


def flatten_list(x):
    return [item for sublist in x for item in sublist]
    # http://stackoverflow.com/questions/952914/making-a-flat-list-out-of-list-of-lists-in-python  # noqa


# =============================================================================
# Randomness
# =============================================================================

def shuffle_list_slice(x, start=None, end=None):
    """Shuffles a segment of a list (in place)."""
    # log.debug("x={}, start={}, end={}".format(x, start, end))
    copy = x[start:end]
    random.shuffle(copy)
    x[start:end] = copy


def shuffle_list_within_chunks(x, chunksize):
    """
    Divides a list into chunks and shuffles WITHIN each chunk (in place).
    For example:
        x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        shuffle_list_within_chunks(x, 4)
    x might now be [4, 1, 3, 2, 7, 5, 6, 8, 9, 12, 11, 10]
                    ^^^^^^^^^^  ^^^^^^^^^^  ^^^^^^^^^^^^^
    """
    starts = list(range(0, len(x), chunksize))
    ends = starts[1:] + [None]
    for start, end in zip(starts, ends):
        shuffle_list_slice(x, start, end)


def shuffle_list_chunks(x, chunksize):
    """
    Divides a list into chunks and shuffles the chunks themselves (in place).
    For example:
        x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        shuffle_list_chunks(x, 4)
    x might now be [5, 6, 7, 8, 1, 2, 3, 4, 9, 10, 11, 12]
                    ^^^^^^^^^^  ^^^^^^^^^^  ^^^^^^^^^^^^^
    """
    starts = list(range(0, len(x), chunksize))
    ends = starts[1:] + [len(x)]
    # Shuffle the indexes rather than the array, then we can write back
    # in place.
    chunks = []
    for start, end in zip(starts, ends):
        chunks.append(list(range(start, end)))
    random.shuffle(chunks)
    indexes = flatten_list(chunks)
    sort_list_by_index_list(x, indexes)


def shuffle_list_subset(x, indexes):
    """Shuffles some elements of a list, specified by index."""
    elements = [x[i] for i in indexes]
    random.shuffle(elements)
    for element_idx, x_idx in enumerate(indexes):
        x[x_idx] = elements[element_idx]


def last_index_of(x, value):
    """Gets the index of the last occurrence of value in the list x."""
    return len(x) - 1 - x[::-1].index(value)


def block_shuffle_by_item(x, indexorder, start=None, end=None):
    """
    Shuffles the list x hierarchically, in place.
    indexorder is a list of indexes of each item of x.
    The first index varies slowest; the last varies fastest.

    For example:

        p = list(itertools.product("ABC", "xyz", "123"))

    x is now a list of tuples looking like ('A', 'x', '1')

        block_shuffle_by_item(p, [0, 1, 2])

    p might now look like:

        C z 1 } all values of "123" appear  } first "xyz" block
        C z 3 } once, but randomized        }
        C z 2 }                             }
                                            }
        C y 2 } next "123" block            }
        C y 1 }                             }
        C y 3 }                             }
                                            }
        C x 3                               }
        C x 2                               }
        C x 1                               }

        A y 3                               } second "xyz" block
        ...                                 } ...

    """
    item_idx_order = indexorder.copy()
    item_idx = item_idx_order.pop(0)

    # 1. Take copy
    sublist = x[start:end]

    # 2. Sort then shuffle in chunks (e.g. at the "ABC" level)
    sublist.sort(key=operator.itemgetter(item_idx))
    # Note below that we must convert things to tuples to put them into
    # sets; if you take a set() of lists, you get
    #   TypeError: unhashable type: 'list'
    unique_values = set(tuple(x[item_idx]) for x in sublist)
    chunks = [
        [i for i, v in enumerate(sublist) if tuple(v[item_idx]) == value]
        for value in unique_values
    ]
    random.shuffle(chunks)
    indexes = flatten_list(chunks)
    sort_list_by_index_list(sublist, indexes)

    # 3. Call recursively (e.g. at the "xyz" level next)
    if item_idx_order:  # more to do?
        starts_ends = [(min(chunk), max(chunk) + 1) for chunk in chunks]
        for s, e in starts_ends:
            block_shuffle_by_item(sublist, item_idx_order, s, e)

    # 4. Write back
    x[start:end] = sublist


def block_shuffle_by_attr(x, attrorder, start=None, end=None):
    """
    Exactly as for block_shuffle_by_item, but by item attribute
    rather than item index number.

    For example:

        p = list(itertools.product("ABC", "xyz", "123"))
        q = [AttrDict({'one': x[0], 'two': x[1], 'three': x[2]}) for x in p]
        block_shuffle_by_attr(q, ['one', 'two', 'three'])
    """
    item_attr_order = attrorder.copy()
    item_attr = item_attr_order.pop(0)
    # 1. Take copy
    sublist = x[start:end]
    # 2. Sort then shuffle in chunks
    sublist.sort(key=operator.attrgetter(item_attr))
    unique_values = set(tuple(getattr(x, item_attr)) for x in sublist)
    chunks = [
        [
            i for i, v in enumerate(sublist)
            if tuple(getattr(v, item_attr)) == value
        ]
        for value in unique_values
    ]
    random.shuffle(chunks)
    indexes = flatten_list(chunks)
    sort_list_by_index_list(sublist, indexes)
    # 3. Call recursively (e.g. at the "xyz" level next)
    if item_attr_order:  # more to do?
        starts_ends = [(min(chunk), max(chunk) + 1) for chunk in chunks]
        for s, e in starts_ends:
            block_shuffle_by_attr(sublist, item_attr_order, s, e)
    # 4. Write back
    x[start:end] = sublist


def shuffle_where_equal_by_attr(x, attrname):
    """
    Shuffles a list x, in place, where list members are equal as judged by the
    attribute attrname.

    For example:

        p = list(itertools.product("ABC", "xyz", "123"))
        q = [AttrDict({'one': x[0], 'two': x[1], 'three': x[2]}) for x in p]
        shuffle_where_equal_by_attr(q, 'three')
    """
    unique_values = set(tuple(getattr(item, attrname)) for item in x)
    for value in unique_values:
        indexes = [
            i for i, item in enumerate(x)
            if tuple(getattr(item, attrname)) == value
        ]
        shuffle_list_subset(x, indexes)


# =============================================================================
# Number printing, e.g. for parity
# =============================================================================

def trunc_if_integer(n):
    if n == int(n):
        return int(n)
    return n


# =============================================================================
# Class to store last match of compiled regex
# =============================================================================
# Based on http://stackoverflow.com/questions/597476/how-to-concisely-cascade-through-multiple-regex-statements-in-python  # noqa

class CompiledRegexMemory(object):
    def __init__(self):
        self.last_match = None

    def match(self, compiled_regex, text):
        self.last_match = compiled_regex.match(text)
        return self.last_match

    def search(self, compiled_regex, text):
        self.last_match = compiled_regex.search(text)
        return self.last_match

    def group(self, n):
        if not self.last_match:
            return None
        return self.last_match.group(n)


# =============================================================================
# Name of calling class/function, for status messages
# =============================================================================

def get_class_from_frame(fr):
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


def get_caller_name(back=0):
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

def ordered_repr(obj, attrlist):
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


def simple_repr(obj):
    """Even simpler."""
    return "<{classname}({kvp})>".format(
        classname=type(obj).__name__,
        kvp=", ".join("{}={}".format(k, repr(v))
                      for k, v in obj.__dict__.items())
    )


# =============================================================================
# Launch external file using OS's launcher
# =============================================================================

def launch_external_file(filename):
    if sys.platform.startswith('linux'):
        subprocess.call(["xdg-open", filename])
    else:
        os.startfile(filename)


# =============================================================================
# Sorting
# =============================================================================

@total_ordering
class MinType(object):
    """Compares less than anything else."""
    def __le__(self, other):
        return True

    def __eq__(self, other):
        return (self is other)


mintype_singleton = MinType()


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
