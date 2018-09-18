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

import operator
import random
from typing import Any, List

from cardinal_pythonlib.lists import flatten_list, sort_list_by_index_list


# =============================================================================
# Randomness
# =============================================================================

def shuffle_list_slice(x: List[Any],
                       start: int = None, end: int = None) -> None:
    """
    Shuffles a segment of a list, ``x[start:end]``, in place.
    """
    # log.debug("x={}, start={}, end={}".format(x, start, end))
    copy = x[start:end]
    random.shuffle(copy)
    x[start:end] = copy


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


def shuffle_list_subset(x: List[Any], indexes: List[int]) -> None:
    """
    Shuffles some elements of a list (in place). The elements to interchange
    (shuffle) as specified by ``indexes``.
    """
    elements = [x[i] for i in indexes]
    random.shuffle(elements)
    for element_idx, x_idx in enumerate(indexes):
        x[x_idx] = elements[element_idx]


def last_index_of(x: List[Any], value: Any) -> int:
    """
    Gets the index of the last occurrence of ``value`` in the list ``x``.
    """
    return len(x) - 1 - x[::-1].index(value)


def block_shuffle_by_item(x: List[Any],
                          indexorder: List[int],
                          start: int = None,
                          end: int = None) -> None:
    """
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
