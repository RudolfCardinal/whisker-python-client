..  docs/source/changelog.rst

..  Copyright © 2011-2018 Rudolf Cardinal (rudolf@pobox.com).
    .
    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at
    .
        http://www.apache.org/licenses/LICENSE-2.0
    .
    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.


Change history
--------------

* 2016-02-10: moved to package format.

* 2016-02-25: v0.2.0; ``colourlog`` renamed ``logsupport``.

* 2016-11-25: v0.3.5

- Python type hints.
- Write ``exit_on_exception`` exceptions to log, not via :func:`print`.
- :class:`whisker.qtclient.WhiskerOwner` offers new ``pingack_received``
signal.

* 2016-12-01: v0.3.6

- Changed from PySide to PyQt5 (fewer bugs).

* 2017-03-23: v0.3.6

- Removed annotations from ``alembic.py``; alembic uses
``inspect.getargspec()``, which chokes with ``ValueError: Function has
keyword-only arguments or annotations...``.
- Support PyQt 5.8, including removing calls to ``QHeaderView.setClickable``,
which has gone: https://doc.qt.io/qt-5/qheaderview.html

* 2016-06-22: v0.1.10

- Updates for Starfeeder.

* 2016-06-23: v0.1.11

- Further updates for Starfeeder; supporting structured handling of
:class:`ClientMessage`.

* 2017: v1.0

- Update for new ``cardinal_pythonlib``.

* 2017-09-07: v1.0.3

- use SQLAlchemy 1.2 ``pool_pre_ping`` feature

* 2018-09-18: v1.0.4

- ``PyQt5`` and ``Twisted`` added as requirements
- Sphinx docs
- updated signal debugging for PyQt5 in ``debug_qt.py``
- general tidy
- ``ValidationError`` removed from ``whisker.qt``; is in
  ``whisker.exceptions`` (previously duplicated)
- additional randomization functions

* 2018-09-21: v1.0.5

- updated required version to ``cardinal_pythonlib>=1.0.26`` in view of
  bugfix there
