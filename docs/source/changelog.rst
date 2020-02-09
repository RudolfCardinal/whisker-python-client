..  docs/source/changelog.rst

..  Copyright © 2011-2020 Rudolf Cardinal (rudolf@pobox.com).
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

**2016-02-10**

- moved to package format

**v0.2.0: 2016-02-25**

- ``colourlog`` renamed ``logsupport``.

**v0.3.5: 2016-11-25**

- Python type hints.
- Write ``exit_on_exception`` exceptions to log, not via :func:`print`.
- :class:`whisker.qtclient.WhiskerOwner` offers new ``pingack_received``
  signal.

**v0.3.6: 2016-12-01**

- Changed from PySide to PyQt5 (fewer bugs).

**v0.3.6: 2017-03-23**

- Removed annotations from ``alembic.py``; alembic uses
  ``inspect.getargspec()``, which chokes with ``ValueError: Function has
  keyword-only arguments or annotations...``.
- Support PyQt 5.8, including removing calls to ``QHeaderView.setClickable``,
  which has gone: https://doc.qt.io/qt-5/qheaderview.html

**v0.1.10: 2016-06-22**

- Updates for Starfeeder.

**v0.1.11: 2016-06-23**

- Further updates for Starfeeder; supporting structured handling of
  :class:`ClientMessage`.

**v1.0: 2017**

- Update for new ``cardinal_pythonlib``.

**v1.0.3: 2017-09-07**

- use SQLAlchemy 1.2 ``pool_pre_ping`` feature

**v1.0.4: 2018-09-18**

- ``PyQt5`` and ``Twisted`` added as requirements
- Sphinx docs
- updated signal debugging for PyQt5 in ``debug_qt.py``
- general tidy
- ``ValidationError`` removed from ``whisker.qt``; is in
  ``whisker.exceptions`` (previously duplicated)
- additional randomization functions

**v1.1.0: 2018-09-21 to 2018-09-22**

- updated required version to ``cardinal_pythonlib>=1.0.26`` in view of
  bugfix there
- there were two classes named ``WhiskerTask``; renamed one to
  ``WhiskerTwistedTask`` and the other to ``WhiskerQtTask``. Also renamed
  ``Whisker`` to ``WhiskerRawSocketClient`` for clarity.
- public docs at https://whiskerpythonclient.readthedocs.io/
- no ``[source]`` links; see
  https://github.com/rtfd/readthedocs.org/issues/2139

  - removed ``typing==3.5.2.2`` dependency and restricted to Python 3.5 (as per
    ``cardinal_pythonlib``) to see if that fixed the autodoc/RTD problem; no
  - no help from changing Sphinx theme either
  - no help from changing ``sys.path`` from ``conf.py``
  - see https://github.com/rtfd/readthedocs.org/issues/2139
  - tried ``/readthedocs.yml`` as per that and
    https://docs.readthedocs.io/en/latest/yaml-config.html

- renamed ``layer_index`` to ``layer_key`` and changed its hint in
  :class:`whisker.random.ShuffleLayerMethod`.

**v1.2.0 to 1.3.0: 2020-02-09**

- Added ``whisker.__version__``.
- :func:`whisker.convenience.load_config_or_die` has a new ``config_filename``
  argument.
- **Requirement for Python 3.6+.** (Because of ``cardinal_pythonlib``.)
- New function :func:`whisker.convenience.update_record`.
