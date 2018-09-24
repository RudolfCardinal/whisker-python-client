#!/usr/bin/env python
# whisker/random.py

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

**Randomization functions that may be used by Whisker tasks.**

"""

from itertools import islice
import logging
import operator
import random
from typing import Any, Callable, Generator, Iterable, List, Sequence

from cardinal_pythonlib.lists import flatten_list, sort_list_by_index_list
from cardinal_pythonlib.reprfunc import auto_repr

log = logging.getLogger(__name__)

SHUFFLE_FUNC_TYPE = Callable[[Sequence[Any]], List[int]]


# =============================================================================
# Basic list functions
# =============================================================================

def last_index_of(x: List[Any], value: Any) -> int:
    """
    Gets the index of the last occurrence of ``value`` in the list ``x``.
    """
    return len(x) - 1 - x[::-1].index(value)


def get_unique_values(iterable: Iterable[Any]) -> List[Any]:
    """
    Gets the unique values of its input.
    See
    https://stackoverflow.com/questions/12897374/get-unique-values-from-a-list-in-python.

    (We don't use ``list(set(x))``, because if the elements of ``x``
    are themselves lists (perfectly common!), that gives ``TypeError:
    unhashable type: 'list'``.)
    """  # noqa
    seen = set()
    result = []
    for element in iterable:
        hashed = element
        if isinstance(element, dict):
            hashed = tuple(sorted(element.items()))
        elif isinstance(element, list):
            hashed = tuple(element)
        if hashed not in seen:
            result.append(element)
            seen.add(hashed)
    return result


def get_indexes_for_value(x: List[Any], value: Any) -> List[int]:
    """
    Returns a list of indexes of ``x`` where its value is ``value``.
    """
    return [i for i, item in enumerate(x) if item == value]


# =============================================================================
# Draw-without-replacement
# =============================================================================

def make_dwor_hat(values: Iterable[Any], multiplier: int = 1) -> List[Any]:
    """
    Makes a "hat" to draw values from. See :func:`gen_dwor`. Does not modify
    the starting list; returns a copy.
    """
    assert multiplier >= 1, "Bad DWOR multiplier"
    hat = []
    for v in values:
        for _ in range(multiplier):
            hat.append(v)
    random.shuffle(hat)  # shuffle in place
    return hat


def gen_dwor(values: Iterable[Any],
             multiplier: int = 1) -> Generator[Any, None, None]:
    """
    Generates values using a draw-without-replacement (DWOR) system.

    Args:
        values: values to generate
        multiplier: DWOR multiplier; see below.

    Yields:
        successive values

    Here's how it works.

    - Suppose ``values == [A, B, C]``.
    - We'll call :math:`n` the number of values (here, 3), and :math:`k` the
      "multiplier" parameter.
    - If you iterate through ``gen_dwor(values, multiplier=1)``, you will
      get a sequence that might look like this (with spaces added for
      clarity):

      .. code-block:: none

        CAB ABC BCA BAC BAC ACB CBA ...

      That is, individual are drawn randomly from a "hat" of size :math:`n =
      3`, containing one of each thing from ``values``. When the hat is empty,
      it is refilled with :math:`n` more.

    - If you iterate through ``gen_dwor(values, multiplier=2)``, however, you
      might get this:

      .. code-block:: none

        AACBBC CABBAC BAACCB ...

      The computer has put :math:`k` copies of each value in the hat, and then
      draws one each time at random (so the hat starts with :math:`nk` values
      in it). When the hat is exhausted, it re-populates.

    The general idea is to provide randomness, but randomness that is
    constrained to prevent unlikely but awkward sequences like

    .. code-block:: none

        AAAAAAAAAAAAAAAA ... unlikely but possible with full randomness!

    yet also have the option to avoid predictability. With :math:`k = 1`, then
    a clever subject could infer exactly what's coming up on every 
    :math:`n`\ th trial. So a low value of :math:`k` brings very few "runs" but
    some predictability; as :math:`k` approaches infinity, it's equivalent to
    full randomness; some reasonably low value of :math:`k` in between may be a
    useful experimental sweet spot.

    See also, for example:

    - http://www.whiskercontrol.com/help/FiveChoice/index.html?fivechoice_dwor.htm

    """  # noqa
    hat = []
    while True:
        if not hat:
            hat = make_dwor_hat(values, multiplier)
        value = hat.pop()
        yield value


def get_dwor_list(values: Iterable[Any],
                  length: int,
                  multiplier: int = 1) -> List[Any]:
    """
    Makes a fixed-length list via :func:`gen_dwor`.

    Args:
        values: values to pick from
        length: list length
        multiplier: DWOR multiplier

    Returns:
        list of length ``length``

    Example:

    .. code-block:: python

        from whisker.random import get_dwor_list
        values = ["a", "b", "c"]
        print(get_dwor_list(values, length=24, multiplier=1))
        print(get_dwor_list(values, length=24, multiplier=2))
        print(get_dwor_list(values, length=24, multiplier=3))

    """
    return list(islice(gen_dwor(values, multiplier), length))


# =============================================================================
# Simple randomness
# =============================================================================

def shuffle_list_slice(x: List[Any],
                       start: int = None, end: int = None) -> None:
    """
    Shuffles a segment of a list, ``x[start:end]``, in place.

    Note that ``start=None`` means "from the beginning" and ``end=None`` means
    "to the end".

    """
    # log.debug("x={}, start={}, end={}".format(x, start, end))
    copy = x[start:end]
    random.shuffle(copy)
    x[start:end] = copy


def shuffle_list_subset(x: List[Any], indexes: List[int]) -> None:
    """
    Shuffles some elements of a list (in place). The elements to interchange
    (shuffle) as specified by ``indexes``.
    """
    elements = [x[i] for i in indexes]
    random.shuffle(elements)
    for element_idx, x_idx in enumerate(indexes):
        x[x_idx] = elements[element_idx]


# =============================================================================
# Randomness within/across chunks
# =============================================================================

def shuffle_list_within_chunks(x: List[Any], chunksize: int) -> None:
    """
    Divides a list into chunks and shuffles WITHIN each chunk (in place).
    For example:

    .. code-block:: python

        x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        shuffle_list_within_chunks(x, 4)

    ``x`` might now be:

    .. code-block:: none

        [4, 1, 3, 2, 7, 5, 6, 8, 9, 12, 11, 10]
         ^^^^^^^^^^  ^^^^^^^^^^  ^^^^^^^^^^^^^
    """
    starts = list(range(0, len(x), chunksize))
    # noinspection PyTypeChecker
    ends = starts[1:] + [None]
    for start, end in zip(starts, ends):
        shuffle_list_slice(x, start, end)


def shuffle_list_chunks(x: List[Any], chunksize: int) -> None:
    """
    Divides a list into chunks and shuffles the chunks themselves (in place).
    For example:

    .. code-block:: python

        x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        shuffle_list_chunks(x, 4)

    ``x`` might now be

    .. code-block:: none

        [5, 6, 7, 8, 1, 2, 3, 4, 9, 10, 11, 12]
         ^^^^^^^^^^  ^^^^^^^^^^  ^^^^^^^^^^^^^

    Uses :func:`cardinal_pythonlib.lists.flatten_list` and
    :func:`cardinal_pythonlib.lists.sort_list_by_index_list`. (I say that
    mainly to test Intersphinx, when it is enabled.)
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


# =============================================================================
# Hierarchical randomness: early methods
# =============================================================================

def block_shuffle_by_item(x: List[Any],
                          indexorder: List[int],
                          start: int = None,
                          end: int = None) -> None:
    """
    **DEPRECATED:** :func:`layered_shuffle` is more powerful.

    Shuffles the list ``x[start:end]`` hierarchically, in place.

    Args:
        x: list to shuffle
        indexorder: a list of indexes of each item of ``x``
            The first index varies slowest; the last varies fastest.
        start: start index of ``x``
        end: end index of ``x``

    For example:

    .. code-block:: python

        p = list(itertools.product("ABC", "xyz", "123"))

    ``x`` is now a list of tuples looking like ``('A', 'x', '1')``.

    .. code-block:: python

        block_shuffle_by_item(p, [0, 1, 2])

    ``p`` might now look like:

    .. code-block:: none

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

    A clearer explanation is in :func:`block_shuffle_by_attr`.

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


def block_shuffle_by_attr(x: List[Any],
                          attrorder: List[str],
                          start: int = None,
                          end: int = None) -> None:
    """
    **DEPRECATED:** :func:`layered_shuffle` is more powerful.

    Exactly as for :func:`block_shuffle_by_item`, but by item attribute
    rather than item index number.

    For example:

    .. code-block:: python

        from collections import namedtuple
        import itertools
        from whisker.random import block_shuffle_by_attr

        p = list(itertools.product("ABC", "xyz", "123"))
        Trio = namedtuple("Trio", ["upper", "lower", "digit"])
        q = [Trio(*x) for x in p]
        block_shuffle_by_attr(q, ['upper', 'lower', 'digit'])

    ``q`` started off as:

    .. code-block:: none

        [
            Trio(upper='A', lower='x', digit='1'),
            Trio(upper='A', lower='x', digit='2'),
            Trio(upper='A', lower='x', digit='3'),
            Trio(upper='A', lower='y', digit='1'),
            Trio(upper='A', lower='y', digit='2'),
            Trio(upper='A', lower='y', digit='3'),
            Trio(upper='A', lower='z', digit='1'),
            Trio(upper='A', lower='z', digit='2'),
            Trio(upper='A', lower='z', digit='3'),
            Trio(upper='B', lower='x', digit='1'),
            Trio(upper='B', lower='x', digit='2'),
            Trio(upper='B', lower='x', digit='3'),
            Trio(upper='B', lower='y', digit='1'),
            Trio(upper='B', lower='y', digit='2'),
            Trio(upper='B', lower='y', digit='3'),
            Trio(upper='B', lower='z', digit='1'),
            Trio(upper='B', lower='z', digit='2'),
            Trio(upper='B', lower='z', digit='3'),
            Trio(upper='C', lower='x', digit='1'),
            Trio(upper='C', lower='x', digit='2'),
            Trio(upper='C', lower='x', digit='3'),
            Trio(upper='C', lower='y', digit='1'),
            Trio(upper='C', lower='y', digit='2'),
            Trio(upper='C', lower='y', digit='3'),
            Trio(upper='C', lower='z', digit='1'),
            Trio(upper='C', lower='z', digit='2'),
            Trio(upper='C', lower='z', digit='3')
        ]

    but after the shuffle ``q`` might now be:

    .. code-block:: none

        [
            Trio(upper='B', lower='z', digit='1'),
            Trio(upper='B', lower='z', digit='3'),
            Trio(upper='B', lower='z', digit='2'),
            Trio(upper='B', lower='x', digit='1'),
            Trio(upper='B', lower='x', digit='3'),
            Trio(upper='B', lower='x', digit='2'),
            Trio(upper='B', lower='y', digit='3'),
            Trio(upper='B', lower='y', digit='2'),
            Trio(upper='B', lower='y', digit='1'),
            Trio(upper='A', lower='z', digit='2'),
            Trio(upper='A', lower='z', digit='1'),
            Trio(upper='A', lower='z', digit='3'),
            Trio(upper='A', lower='x', digit='1'),
            Trio(upper='A', lower='x', digit='2'),
            Trio(upper='A', lower='x', digit='3'),
            Trio(upper='A', lower='y', digit='3'),
            Trio(upper='A', lower='y', digit='1'),
            Trio(upper='A', lower='y', digit='2'),
            Trio(upper='C', lower='x', digit='2'),
            Trio(upper='C', lower='x', digit='3'),
            Trio(upper='C', lower='x', digit='1'),
            Trio(upper='C', lower='y', digit='2'),
            Trio(upper='C', lower='y', digit='1'),
            Trio(upper='C', lower='y', digit='3'),
            Trio(upper='C', lower='z', digit='1'),
            Trio(upper='C', lower='z', digit='2'),
            Trio(upper='C', lower='z', digit='3')
        ]

    You can see that the ``A``/``B``/``C`` group has been shuffled as blocks.
    Then, within ``B``, the ``x``/``y``/``z`` groups have been shuffled (and so
    on for ``A`` and ``C``). Then, within ``B.z``, the ``1``/``2``/``3`` values
    have been shuffled (and so on).

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


def shuffle_where_equal_by_attr(x: List[Any], attrname: str) -> None:
    """
    **DEPRECATED:** :func:`layered_shuffle` is more powerful.

    Shuffles a list ``x``, in place, where list members are equal as judged by
    the attribute ``attrname``.

    This is easiest to show by example:

    .. code-block:: python

        from collections import namedtuple
        import itertools
        from whisker.random import shuffle_where_equal_by_attr

        p = list(itertools.product("ABC", "xyz", "123"))
        Trio = namedtuple("Trio", ["upper", "lower", "digit"])
        q = [Trio(*x) for x in p]
        shuffle_where_equal_by_attr(q, 'digit')

    ``q`` started off as:

    .. code-block:: none

        [
            Trio(upper='A', lower='x', digit='1'),
            Trio(upper='A', lower='x', digit='2'),
            Trio(upper='A', lower='x', digit='3'),
            Trio(upper='A', lower='y', digit='1'),
            Trio(upper='A', lower='y', digit='2'),
            Trio(upper='A', lower='y', digit='3'),
            Trio(upper='A', lower='z', digit='1'),
            Trio(upper='A', lower='z', digit='2'),
            Trio(upper='A', lower='z', digit='3'),
            Trio(upper='B', lower='x', digit='1'),
            Trio(upper='B', lower='x', digit='2'),
            Trio(upper='B', lower='x', digit='3'),
            Trio(upper='B', lower='y', digit='1'),
            Trio(upper='B', lower='y', digit='2'),
            Trio(upper='B', lower='y', digit='3'),
            Trio(upper='B', lower='z', digit='1'),
            Trio(upper='B', lower='z', digit='2'),
            Trio(upper='B', lower='z', digit='3'),
            Trio(upper='C', lower='x', digit='1'),
            Trio(upper='C', lower='x', digit='2'),
            Trio(upper='C', lower='x', digit='3'),
            Trio(upper='C', lower='y', digit='1'),
            Trio(upper='C', lower='y', digit='2'),
            Trio(upper='C', lower='y', digit='3'),
            Trio(upper='C', lower='z', digit='1'),
            Trio(upper='C', lower='z', digit='2'),
            Trio(upper='C', lower='z', digit='3')
        ]

    but after the shuffle ``q`` might now be:

    .. code-block:: none

        [
            Trio(upper='A', lower='x', digit='1'),
            Trio(upper='A', lower='y', digit='2'),
            Trio(upper='A', lower='z', digit='3'),
            Trio(upper='B', lower='z', digit='1'),
            Trio(upper='A', lower='z', digit='2'),
            Trio(upper='C', lower='x', digit='3'),
            Trio(upper='B', lower='y', digit='1'),
            Trio(upper='A', lower='x', digit='2'),
            Trio(upper='C', lower='y', digit='3'),
            Trio(upper='A', lower='y', digit='1'),
            Trio(upper='C', lower='y', digit='2'),
            Trio(upper='C', lower='z', digit='3'),
            Trio(upper='C', lower='y', digit='1'),
            Trio(upper='C', lower='z', digit='2'),
            Trio(upper='A', lower='y', digit='3'),
            Trio(upper='B', lower='x', digit='1'),
            Trio(upper='B', lower='z', digit='2'),
            Trio(upper='B', lower='y', digit='3'),
            Trio(upper='C', lower='z', digit='1'),
            Trio(upper='C', lower='x', digit='2'),
            Trio(upper='B', lower='z', digit='3'),
            Trio(upper='C', lower='x', digit='1'),
            Trio(upper='B', lower='x', digit='2'),
            Trio(upper='A', lower='x', digit='3'),
            Trio(upper='A', lower='z', digit='1'),
            Trio(upper='B', lower='y', digit='2'),
            Trio(upper='B', lower='x', digit='3')
        ]

    As you can see, the ``digit`` attribute seems to have stayed frozen and
    everything else has jumbled. What has actually happened is that everything
    with ``digit == 1`` has been shuffled among themselves, and similarly for
    ``digit == 2`` and ``digit == 3``.

    """
    unique_values = set(tuple(getattr(item, attrname)) for item in x)
    for value in unique_values:
        indexes = [
            i for i, item in enumerate(x)
            if tuple(getattr(item, attrname)) == value
        ]
        shuffle_list_subset(x, indexes)


# =============================================================================
# Hierarchical randomness: full power
# =============================================================================

def random_shuffle_indexes(x: List[Any]) -> List[int]:
    """
    Returns a list of indexes of ``x``, randomly shuffled.
    """
    indexes = list(range(len(x)))
    random.shuffle(indexes)  # in place
    return indexes


def block_shuffle_indexes_by_value(x: List[Any]) -> List[int]:
    """
    Returns a list of indexes of ``x``, block-shuffled by value.

    That is: we aggregate items into blocks, defined by value, and shuffle
    those blocks, returning the corresponding indexes of the original list.
    """
    unique_values = get_unique_values(x)
    list_of_chunks = [
        get_indexes_for_value(x, value)
        for value in unique_values
    ]
    random.shuffle(list_of_chunks)
    indexes = flatten_list(list_of_chunks)
    return indexes


def dwor_shuffle_indexes(x: List[Any], multiplier: int = 1) -> List[int]:
    """
    Returns a list of indexes of ``x``, DWOR-shuffled by value.

    This is a bit tricky as we don't have a guarantee of equal numbers. It
    does sensible things in those circumstances.
    """
    assert multiplier >= 1, "Bad DWOR multiplier"
    unique_values = get_unique_values(x)
    list_of_chunks = [
        get_indexes_for_value(x, value)
        for value in unique_values
    ]

    def unusual_make_dwor_hat() -> List[int]:
        hat_ = []
        for _ in range(multiplier):
            for chunk in list_of_chunks:
                if chunk:
                    hat_.append(chunk.pop(0))
        random.shuffle(hat_)  # in place
        return hat_

    hat = []
    indexes = []  # type: List[int]
    finished = False
    while not finished:
        if not hat:
            hat = unusual_make_dwor_hat()
        if hat:
            indexes.append(hat.pop())
        else:
            finished = True
    return indexes


def sort_indexes(x: List[Any]) -> List[int]:
    """
    Returns the indexes of ``x`` in an order that would sort ``x`` by value.
    
    See https://stackoverflow.com/questions/7851077/how-to-return-index-of-a-sorted-list
    """  # noqa
    return sorted(range(len(x)), key=lambda index: x[index])


def reverse_sort_indexes(x: List[Any]) -> List[int]:
    """
    Returns the indexes of ``x`` in an order that would reverse-sort ``x`` by
    value.
    """
    return sorted(range(len(x)), key=lambda index: x[index], reverse=True)


class ShuffleLayerMethod(object):
    """
    Class to representing instructions to :func:`layered_shuffle` (q.v.).
    """
    def __init__(self,
                 flat: bool = False,
                 layer_key: int = None,
                 layer_attr: str = None,
                 layer_func: Callable[[Any], Any] = None,
                 shuffle_func: SHUFFLE_FUNC_TYPE = None) -> None:
        """
        Args:
            flat: take data as ``x[index]``?
            layer_key: take data as ``x[index][layer_key]``?
            layer_attr: take data as ``getattr(x[index], layer_attr)``?
            layer_func: take data as ``layer_func(x[index])``?
            shuffle_func: function (N.B. may be a lambda function with
                parameters attached) that takes a list of objects and returns
                a list of INDEXES, suitably shuffled.

        Typical values of ``shuffle_func``:

        - ``None``: no shuffle
        - ``random_shuffle_indexes``: plain shuffle; see
          :func:`random_shuffle_indexes`
        - ``dwor_shuffle_indexes``: DWOR-style shuffle (will need a ``lambda``
          for its ``multiplier parameter``; see :func:`dwor_shuffle_indexes`
        - ``block_shuffle_indexes_by_value``: aggregate items into blocks,
          defined by value, and shuffle those blocks; see
          :func:`block_shuffle_indexes_by_value`
        - ``sort_indexes``: not exactly shuffling! See :func:`sort_indexes`.
        - ``reverse_sort_indexes``: not exactly shuffling! See
          :func:`reverse_sort_indexes`.

        """
        assert (
            flat +
            (layer_key is not None) +
            bool(layer_attr)
        ) == 1, "Specify exactly one way of accessing data from the layer!"
        if layer_key is not None:
            assert isinstance(layer_key, int)
            assert layer_key > 0
        elif layer_attr:
            assert isinstance(layer_attr, str)
        elif layer_func:
            assert callable(layer_func)
        self.flat = flat
        self.layer_key = layer_key
        self.layer_attr = layer_attr
        self.layer_func = layer_func
        self.shuffle_func = shuffle_func

    def __repr__(self) -> str:
        return auto_repr(self)

    def get_values(self, x: List[Any]) -> List[Any]:
        """
        Returns all the values of interest from ``x`` for this layer.
        """
        if self.flat:
            return x[:]  # a copy, just in case someone wants to modify it
        elif self.layer_attr:
            attr = self.layer_attr
            return [getattr(item, attr) for item in x]
        elif self.layer_func:
            func = self.layer_func
            return [func(item) for item in x]
        else:
            # key, via item[key], meaning item.__getitem__(key)
            key = self.layer_key
            return [item[key] for item in x]

    def get_unique_values(self, x: List[Any]) -> List[Any]:
        """
        Returns all the unique values of ``x`` for this layer.
        """
        return get_unique_values(self.get_values(x))

    def get_indexes_for_value(self, x: List[Any], value: Any) -> List[int]:
        """
        Returns a list of indexes of ``x`` where its value (as defined by this
        layer) is ``value``.
        """
        return get_indexes_for_value(self.get_values(x), value)


def layered_shuffle(x: List[Any],
                    layers: List[ShuffleLayerMethod]) -> None:
    r"""
    Most powerful hierarchical shuffle command here.

    Shuffles ``x`` in place in a layered way as specified by the sequence of
    methods.
    
    In more detail:
    
    - for each layer, it shuffles values of ``x`` as defined by the
      :class:`ShuffleLayerMethod` (for example: "shuffle ``x`` in blocks based
      on the value of ``x.someattr``", or "shuffle ``x`` randomly")
    - it then proceeds to deeper layers *within* sub-lists defined by each
      unique value from the previous layer. 

    Args:
        x: sequence (e.g. list) to shuffle
        layers: list of :class:`ShuffleLayerMethod` instructions

    Examples:

    .. code-block:: python

        from collections import namedtuple
        import itertools
        import logging
        import random
        from whisker.random import *
        logging.basicConfig(level=logging.DEBUG)
        
        startlist = ["a", "b", "c", "d", "a", "b", "c", "d", "a", "b", "c", "d"]
        x1 = startlist[:]
        x2 = startlist[:]
        x3 = startlist[:]
        x4 = startlist[:]
        
        do_nothing_method = ShuffleLayerMethod(flat=True, shuffle_func=None)
        do_nothing_method.get_unique_values(x1)
        do_nothing_method.get_indexes_for_value(x1, "b")
        
        layered_shuffle(x1, [do_nothing_method])
        print(x1)
        
        flat_randomshuffle_method = ShuffleLayerMethod(
            flat=True, shuffle_func=random_shuffle_indexes)
        flat_randomshuffle_method.get_unique_values(x1)
        flat_randomshuffle_method.get_indexes_for_value(x1, "b")
        layered_shuffle(x1, [flat_randomshuffle_method])
        print(x1)
        
        flat_blockshuffle_method = ShuffleLayerMethod(
            flat=True, shuffle_func=block_shuffle_indexes_by_value)
        layered_shuffle(x2, [flat_blockshuffle_method])
        print(x2)
        
        flat_dworshuffle_method = ShuffleLayerMethod(
            flat=True, shuffle_func=dwor_shuffle_indexes)
        layered_shuffle(x3, [flat_dworshuffle_method])
        print(x3)
        
        flat_dworshuffle2_method = ShuffleLayerMethod(
            flat=True, shuffle_func=lambda x: dwor_shuffle_indexes(x, multiplier=2))
        layered_shuffle(x4, [flat_dworshuffle2_method])
        print(x4)
        
        p = list(itertools.product("ABC", "xyz", "123"))
        Trio = namedtuple("Trio", ["upper", "lower", "digit"])
        q = [Trio(*x) for x in p]
        print("\n".join(str(x) for x in q))
        
        upper_method = ShuffleLayerMethod(
            layer_attr="upper", shuffle_func=block_shuffle_indexes_by_value)
        lower_method = ShuffleLayerMethod(
            layer_attr="lower", shuffle_func=reverse_sort_indexes)
        digit_method = ShuffleLayerMethod(
            layer_attr="digit", shuffle_func=random_shuffle_indexes)
        
        layered_shuffle(q, [upper_method, lower_method, digit_method])
        print("\n".join(str(x) for x in q))

    """  # noqa
    if not layers:
        return
    layer = layers[0]
    subsequent_layers = layers[1:]

    if layer.shuffle_func:
        values = layer.get_values(x)
        shuffled_indexes = layer.shuffle_func(values)
        log.debug("Applying function {!r} to values {!r} gives indexes "
                  "{!r}".format(layer.shuffle_func, values, shuffled_indexes))
        sort_list_by_index_list(x, shuffled_indexes)

    if subsequent_layers:
        unique_values = layer.get_unique_values(x)
        for value in unique_values:
            indexes_for_value = layer.get_indexes_for_value(x, value)
            subelements = [x[i] for i in indexes_for_value]
            # Recursion:
            layered_shuffle(subelements, subsequent_layers)
            # Put the (shuffled( elements back:
            for element_idx, x_idx in enumerate(indexes_for_value):
                x[x_idx] = subelements[element_idx]
