#!/usr/bin/env python
# whisker/qt.py

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

**Qt classes for Whisker GUI tasks.**

"""


from functools import wraps
import gc
import logging
import sys
import threading
import traceback
from typing import Any, Iterable, List, Optional, Tuple, Type

from cardinal_pythonlib.debugging import get_caller_name
from cardinal_pythonlib.lists import contains_duplicates
from cardinal_pythonlib.logs import HtmlColorHandler
from cardinal_pythonlib.sort import attrgetter_nonesort, methodcaller_nonesort
# noinspection PyPackageRequirements
from PyQt5.QtCore import (
    QAbstractListModel,
    QAbstractTableModel,
    QEvent,
    QModelIndex,
    QObject,
    Qt,
    QTimer,
    # QVariant,  # non-existent in PySide?
    pyqtSignal,
    pyqtSlot,
)
# noinspection PyPackageRequirements
from PyQt5.QtCore import (
    QItemSelection,
    QItemSelectionModel,
)
# noinspection PyPackageRequirements
from PyQt5.QtGui import (
    QCloseEvent,  # for type hints
    QTextCursor,
)
# noinspection PyPackageRequirements
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLayout,  # for type hints
    QListView,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QTableView,
    # QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session  # for type hints

log = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

NOTHING_SELECTED = -1  # e.g. http://doc.qt.io/qt-4.8/qbuttongroup.html#id


# =============================================================================
# Exceptions
# =============================================================================

class EditCancelledException(Exception):
    """
    Exception to represent that the user cancelled editing.
    """
    pass


# =============================================================================
# Styled elements
# =============================================================================

GROUPBOX_STYLESHEET = """
QGroupBox {
    border: 1px solid gray;
    border-radius: 2px;
    margin-top: 0.5em;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 2px 0 2px;
}
"""
# http://stackoverflow.com/questions/14582591/border-of-qgroupbox
# http://stackoverflow.com/questions/2730331/set-qgroupbox-title-font-size-with-style-sheets  # noqa


class StyledQGroupBox(QGroupBox):
    """
    :class:`QGroupBox` that applies a specific CSS stylesheet.
    """
    def __init__(self, *args) -> None:
        super().__init__(*args)
        self.setStyleSheet(GROUPBOX_STYLESHEET)


# =============================================================================
# LogWindow
# =============================================================================

LOGEDIT_STYLESHEET = """
QPlainTextEdit {
    border: 1px solid black;
    font-family: 'Dejavu Sans Mono', 'Courier';
    font-size: 10pt;
    background-color: black;
    color: white;
}
"""


class LogWindow(QMainWindow):
    """
    Hard-to-close dialog-style box for a GUI Python log window.

    A :class:`QMainWindow` that provides a a console-style view on a Python
    log, and provides copying facilities.

    It achieves this by adding a new handler to that log.

    Use this window when you wish to do nothing except show progress from
    an application that uses the log. (Typically you would pass the root
    logger to this window, so all log output is seen.)

    Signals:

    - ``emit_msg(str)``
    """
    emit_msg = pyqtSignal(str)

    # noinspection PyArgumentList
    def __init__(self,
                 level: int = logging.INFO,
                 window_title: str = "Python log",
                 logger: logging.Logger = None,
                 min_width: int = 800,
                 min_height: int = 400,
                 maximum_block_count: int = 1000) -> None:
        """
        Args:
            level: Python log level
            window_title: window title
            logger: Python logger
            min_width: minimum window width in pixels
            min_height: minimum window height in pixels
            maximum_block_count: maxmium number of blocks (in this case:
                log entries) that the window will hold
        """
        super().__init__()
        self.setStyleSheet(LOGEDIT_STYLESHEET)

        self.handler = HtmlColorHandler(self.log_message, level)
        self.may_close = False
        self.set_may_close(self.may_close)

        self.setWindowTitle(window_title)
        if min_width:
            self.setMinimumWidth(min_width)
        if min_height:
            self.setMinimumHeight(min_height)

        log_group = StyledQGroupBox("Log")
        log_layout_1 = QVBoxLayout()
        log_layout_2 = QHBoxLayout()
        self.log = QPlainTextEdit()
        # QPlainTextEdit better than QTextEdit because it supports
        # maximumBlockCount while still allowing HTML (via appendHtml,
        # not insertHtml).
        self.log.setReadOnly(True)
        self.log.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.log.setMaximumBlockCount(maximum_block_count)
        log_clear_button = QPushButton('Clear log')
        # noinspection PyUnresolvedReferences
        log_clear_button.clicked.connect(self.log.clear)
        log_copy_button = QPushButton('Copy to clipboard')
        # noinspection PyUnresolvedReferences
        log_copy_button.clicked.connect(self.copy_whole_log)
        log_layout_2.addWidget(log_clear_button)
        log_layout_2.addWidget(log_copy_button)
        log_layout_2.addStretch()
        log_layout_1.addWidget(self.log)
        log_layout_1.addLayout(log_layout_2)
        log_group.setLayout(log_layout_1)

        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.addWidget(log_group)

        self.emit_msg.connect(self.log_internal)

        if logger:
            logger.addHandler(self.get_handler())

    def get_handler(self) -> logging.Handler:
        """
        Returns the log's handler (for this window).
        """
        return self.handler

    def set_may_close(self, may_close: bool) -> None:
        """
        Sets the ``may_close`` property, and enable/disable the "close window"
        button accordingly.
        """
        # log.debug("LogWindow: may_close({})".format(may_close))
        self.may_close = may_close
        # return
        if may_close:
            self.setWindowFlags(self.windowFlags() | Qt.WindowCloseButtonHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
        self.show()
        # ... or it will be hidden (in a logical not a real way!) by
        # setWindowFlags(), and thus mess up the logic for the whole Qt app
        # exiting (since qt_app.exec_() runs until there are no more windows
        # being shown).

    def copy_whole_log(self) -> None:
        """
        Copies the contents of the log to the clipboard.
        """
        # Ctrl-C will copy the selected parts.
        # log.copy() will copy the selected parts.
        self.log.selectAll()
        self.log.copy()
        self.log.moveCursor(QTextCursor.End)
        self.scroll_to_end_of_log()

    def scroll_to_end_of_log(self) -> None:
        """
        Scrolls the window to show the most recent entry.
        """
        vsb = self.log.verticalScrollBar()
        vsb.setValue(vsb.maximum())
        hsb = self.log.horizontalScrollBar()
        hsb.setValue(0)

    # noinspection PyPep8Naming
    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Trap the "please close" event, and say no if the ``may_close``
        property is not set.
        """
        if not self.may_close:
            # log.debug("LogWindow: ignore closeEvent")
            event.ignore()
        else:
            # log.debug("LogWindow: accept closeEvent")
            event.accept()

    def log_message(self, html: str) -> None:
        """
        Passes a message (in HTML format) to the :func:`log_internal`
        function (which may be running in a different thread).
        """
        # Jump threads via a signal
        self.emit_msg.emit(html)

    # noinspection PyArgumentList
    @pyqtSlot(str)
    def log_internal(self, html: str) -> None:
        """
        Adds an HTML-formatted message to the text shown in our window.
        """
        # self.log.moveCursor(QTextCursor.End)
        # self.log.insertHtml(html)
        self.log.appendHtml(html)
        # self.scroll_to_end_of_log()
        # ... unnecessary; if you're at the end, it scrolls, and if you're at
        # the top, it doesn't bug you.

    # noinspection PyArgumentList
    @pyqtSlot()
    def exit(self) -> None:
        """
        Forces this window to close.
        """
        # log.debug("LogWindow: exit")
        self.may_close = True
        # closed = QMainWindow.close(self)
        # log.debug("closed: {}".format(closed))
        QMainWindow.close(self)

    # noinspection PyArgumentList
    @pyqtSlot()
    def may_exit(self) -> None:
        """
        Calls ``set_may_close(True)`` to enable this window to close.
        """
        # log.debug("LogWindow: may_exit")
        self.set_may_close(True)


# =============================================================================
# TextLogElement
# =============================================================================

class TextLogElement(object):
    """
    Add a text log to your dialog box.

    Encapsulates a :class:`QWidget` representing a textual log in a group box.

    Use this to embed a log within another Qt dialogue.

     (This is nothing to do with the Python ``logging`` logs.)
    """

    # noinspection PyArgumentList
    def __init__(self,
                 maximum_block_count: int = 1000,
                 font_size_pt: int = 10,
                 font_family: str = "Courier",
                 title: str = "Log") -> None:
        """
        Args:
            maximum_block_count: the maximum number of blocks (log entries)
                to show in this window
            font_size_pt: font size, in points
            font_family: font family
            title: title for group box
        """
        # For nested layouts: (1) create everything, (2) lay out
        self.log_group = StyledQGroupBox(title)
        log_layout_1 = QVBoxLayout()
        log_layout_2 = QHBoxLayout()
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.log.setMaximumBlockCount(maximum_block_count)

        font = self.log.font()
        font.setFamily(font_family)
        font.setPointSize(font_size_pt)

        log_clear_button = QPushButton('Clear log')
        # noinspection PyUnresolvedReferences
        log_clear_button.clicked.connect(self.log.clear)
        log_copy_button = QPushButton('Copy to clipboard')
        # noinspection PyUnresolvedReferences
        log_copy_button.clicked.connect(self.copy_whole_log)
        log_layout_2.addWidget(log_clear_button)
        log_layout_2.addWidget(log_copy_button)
        log_layout_2.addStretch(1)
        log_layout_1.addWidget(self.log)
        log_layout_1.addLayout(log_layout_2)
        self.log_group.setLayout(log_layout_1)

    def get_widget(self) -> QWidget:
        """
        Returns:
            a :class:`QWidget` that is the group box containing the log
            and its controls
        """
        return self.log_group

    def add(self, msg: str) -> None:
        """
        Adds a message to the log.
        """
        # http://stackoverflow.com/questions/16568451
        # self.log.moveCursor(QTextCursor.End)
        self.log.appendPlainText(msg)
        # ... will append it as a *paragraph*, i.e. no need to add a newline
        # self.scroll_to_end_of_log()

    def copy_whole_log(self) -> None:
        """
        Copies the log to the clipboard.
        """
        # Ctrl-C will copy the selected parts.
        # log.copy() will copy the selected parts.
        self.log.selectAll()
        self.log.copy()
        self.log.moveCursor(QTextCursor.End)
        self.scroll_to_end_of_log()

    def scroll_to_end_of_log(self) -> None:
        """
        Scrolls the log so that the last entry is visible.
        """
        vsb = self.log.verticalScrollBar()
        vsb.setValue(vsb.maximum())
        hsb = self.log.horizontalScrollBar()
        hsb.setValue(0)


# =============================================================================
# StatusMixin
# =============================================================================

class StatusMixin(object):
    """
    Add this to a :class:`QObject` to provide easy Python logging and Qt
    signal-based status/error messaging.

    It emits status messages to a Python log and to Qt signals.

    Uses the same function names as Python logging, for predictability.

    Signals:

    - ``status_sent(str, str)``
    - ``error_sent(str, str)``
    """
    status_sent = pyqtSignal(str, str)
    error_sent = pyqtSignal(str, str)

    def __init__(self,
                 name: str,
                 logger: logging.Logger,
                 thread_info: bool = True,
                 caller_info: bool = True,
                 **kwargs) -> None:
        """
        Args:
            name: name to add to log output
            logger: Python logger to send output to
            thread_info: show thread information as part of the output?
            caller_info: add information about the function that sent the
                message?
            kwargs: additional parameters for superclass (required for mixins)
        """
        # Somewhat verbose names to make conflict with a user class unlikely.
        super().__init__(**kwargs)
        self._statusmixin_name = name
        self._statusmixin_log = logger
        self._statusmixin_debug_thread_info = thread_info
        self._statusmixin_debug_caller_info = caller_info

    def _process_status_message(self, msg: str) -> str:
        """
        Args:
            msg: a log message

        Returns:
            a version with descriptive information added

        """
        callerinfo = ''
        if self._statusmixin_debug_caller_info:
            callerinfo = "{}:".format(get_caller_name(back=1))
        threadinfo = ''
        if self._statusmixin_debug_thread_info:
            # msg += (
            #     " [QThread={}, name={}, ident={}]".format(
            #         QThread.currentThread(),
            #         # int(QThread.currentThreadId()),
            #         threading.current_thread().name,
            #         threading.current_thread().ident,
            #     )
            # )
            threadinfo = " [thread {}]".format(threading.current_thread().name)
        return "{}:{} {}{}".format(self._statusmixin_name, callerinfo, msg,
                                   threadinfo)

    # noinspection PyArgumentList
    @pyqtSlot(str)
    def debug(self, msg: str) -> None:
        """
        Writes a debug-level log message.
        """
        self._statusmixin_log.debug(self._process_status_message(msg))

    # noinspection PyArgumentList
    @pyqtSlot(str)
    def critical(self, msg: str) -> None:
        """
        Writes a critical-level log message, and triggers the
        ``error_sent`` signal.
        """
        self._statusmixin_log.critical(self._process_status_message(msg))
        self.error_sent.emit(msg, self._statusmixin_name)

    # noinspection PyArgumentList
    @pyqtSlot(str)
    def error(self, msg: str) -> None:
        """
        Writes a error-level log message, and triggers the
        ``error_sent`` signal.
        """
        self._statusmixin_log.error(self._process_status_message(msg))
        self.error_sent.emit(msg, self._statusmixin_name)

    # noinspection PyArgumentList
    @pyqtSlot(str)
    def warning(self, msg: str) -> None:
        """
        Writes a warning-level log message, and triggers the
        ``error_sent`` signal.
        """
        # warn() is deprecated; use warning()
        self._statusmixin_log.warning(self._process_status_message(msg))
        self.error_sent.emit(msg, self._statusmixin_name)

    # noinspection PyArgumentList
    @pyqtSlot(str)
    def info(self, msg: str) -> None:
        """
        Writes an info-level log message, and triggers the
        ``status_sent`` signal.
        """
        self._statusmixin_log.info(self._process_status_message(msg))
        self.status_sent.emit(msg, self._statusmixin_name)

    # noinspection PyArgumentList
    @pyqtSlot(str)
    def status(self, msg: str) -> None:
        """
        Writes an info-level log message, and triggers the
        ``status_sent`` signal.
        """
        # Don't just call info, because of the stack-counting thing
        # in _process_status_message
        self._statusmixin_log.info(self._process_status_message(msg))
        self.status_sent.emit(msg, self._statusmixin_name)


# =============================================================================
# TransactionalEditDialogMixin
# =============================================================================

class TransactionalEditDialogMixin(object):
    """
    Mixin for a config-editing dialogue. Use it as:

    .. code-block:: python

        class MyEditingDialog(TransactionalEditDialogMixin, QDialog):
            pass

    Wraps the editing in a ``SAVEPOINT`` transaction.
    The caller must still ``commit()`` afterwards, but any rollbacks are
    automatic.

    See also http://pyqt.sourceforge.net/Docs/PyQt5/multiinheritance.html
    for the ``super().__init__(..., **kwargs)`` chain.

    Signals:

    - ``ok()``

    """
    ok = pyqtSignal()

    # noinspection PyArgumentList, PyUnresolvedReferences
    def __init__(self, session: Session, obj: object, layout: QLayout,
                 readonly: bool = False, **kwargs) -> None:
        """
        Args:
            session: SQLAlchemy :class:`Session`
            obj: SQLAlchemy ORM object being edited
            layout: Qt class`QLayout` to encapsulate within the
                class:`QDialog`'s main layout. This should contain all the
                editing widgets. The mixin wraps that with OK/cancel buttons.
            readonly: make this a read-only view
            kwargs: additional parameters to superclass
        """
        super().__init__(**kwargs)

        # Store variables
        self.obj = obj
        self.session = session
        self.readonly = readonly

        # Add OK/cancel buttons to layout thus far
        if readonly:
            ok_cancel_buttons = QDialogButtonBox(
                QDialogButtonBox.Cancel,
                Qt.Horizontal,
                self)
            ok_cancel_buttons.rejected.connect(self.reject)
        else:
            ok_cancel_buttons = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                Qt.Horizontal,
                self)
            ok_cancel_buttons.accepted.connect(self.ok_clicked)
            ok_cancel_buttons.rejected.connect(self.reject)

        # Build overall layout
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(layout)
        main_layout.addWidget(ok_cancel_buttons)

    # noinspection PyArgumentList
    @pyqtSlot()
    def ok_clicked(self) -> None:
        """
        Slot for the "OK clicked" signal. Validates the data through
        :func:`dialog_to_object`, and if it passes, calls the Qt
        :func:`accept` function. Otherwise, refuse to close and show
        the validation error.
        """
        try:
            self.dialog_to_object(self.obj)
            # noinspection PyUnresolvedReferences
            self.accept()
        except Exception as e:
            # noinspection PyCallByClass
            QMessageBox.about(self, "Invalid data", str(e))
            # ... str(e) will be a simple message for ValidationError

    def edit_in_nested_transaction(self) -> int:
        """
        Pops up the dialog, allowing editing.

        - Does so within a database transaction.
        - If the user clicks OK *and* the data validates, commits the
          transaction.
        - If the user cancels, rolls back the transaction.
        - We want it nestable, so that the config dialog box can edit part of
          the config, reversibly, without too much faffing around.
          
        *Development notes:*

        - We could nest using SQLAlchemy's support for nested transactions,
          which works whether or not the database itself supports nested
          transactions via the ``SAVEPOINT`` method.
        - With sessions, one must use ``autocommit=True`` and the
          ``subtransactions`` flag; these are virtual transactions handled by
          SQLAlchemy.
        - Alternatively one can use ``begin_nested()`` or
          ``begin(nested=True)``, which uses ``SAVEPOINT``.
        - The following databases support the ``SAVEPOINT`` method:
        
          - MySQL with InnoDB
          - SQLite, from v3.6.8 (2009)
          - PostgreSQL
          
        - Which is better? The author suggests ``SAVEPOINT`` for most applications
          (https://groups.google.com/forum/#!msg/sqlalchemy/CaZyyMx7_8Y/otM0BzDyaigJ).
          Regarding subtransactions: "When a rollback is issued, the
          subtransaction will directly roll back the innermost real
          transaction, however each subtransaction still must be explicitly
          rolled back to maintain proper stacking of subtransactions." So it's
          not as simple as you might guess.
        - See:
        
          - http://docs.sqlalchemy.org/en/latest/core/connections.html
          - http://docs.sqlalchemy.org/en/latest/orm/session_transaction.html
          - http://stackoverflow.com/questions/2336950/transaction-within-transaction
          - http://stackoverflow.com/questions/1306869/are-nested-transactions-allowed-in-mysql
          - https://en.wikipedia.org/wiki/Savepoint
          - http://www.sqlite.org/lang_savepoint.html
          - http://stackoverflow.com/questions/1654857/nested-transactions-with-sqlalchemy-and-sqlite

        - Let's use the ``SAVEPOINT`` technique.

        - No. Even this fails:
        
          .. code-block:: python

            with self.session.begin_nested():
                self.config.port = 5000

        - We were aiming for this:
        
          .. code-block:: python

            try:
                with self.session.begin_nested():
                    result = self.exec_()  # enforces modal
                    if result == QDialog.Accepted:
                        logger.debug("Config changes accepted;  will be committed")
                    else:
                        logger.debug("Config changes cancelled")
                        raise EditCancelledException()
            except EditCancelledException:
                logger.debug("Config changes rolled back.")
            except:
                logger.debug("Exception within nested transaction. "
                             "Config changes will be rolled back.")
                raise
                # Other exceptions will be handled as normal.

        - No... the commit fails, and this SQL is emitted:
        
          .. code-block:: sql
          
            SAVEPOINT sa_savepoint_1
            UPDATE table SET field=?
            RELEASE SAVEPOINT sa_savepoint_1  -- sensible
            ROLLBACK TO SAVEPOINT sa_savepoint_1  -- not sensible
            -- raises sqlite3.OperationalError: no such savepoint: sa_savepoint_1

        - May be this bug:
        
          - https://www.mail-archive.com/sqlalchemy@googlegroups.com/msg28381.html
          - http://bugs.python.org/issue10740
          - https://groups.google.com/forum/#!topic/sqlalchemy/1QelhQ19QsE

        - The bugs are detailed in ``sqlalchemy/dialects/sqlite/pysqlite.py``;
           see "Serializable isolation / Savepoints / Transactional DDL"

        - We work around it by adding hooks to the engine as per that advice;
          see ``db.py``

        """  # noqa
        # A context manager provides cleaner error handling than explicit
        # begin_session() / commit() / rollback() calls.
        # The context manager provided by begin_nested() will commit, or roll
        # back on an exception.
        result = None
        if self.readonly:
            # noinspection PyUnresolvedReferences
            return self.exec_()  # enforces modal
        try:
            with self.session.begin_nested():
                # noinspection PyUnresolvedReferences
                result = self.exec_()  # enforces modal
                if result == QDialog.Accepted:
                    return result
                else:
                    raise EditCancelledException()
        except EditCancelledException:
            log.debug("Dialog changes have been rolled back.")
            return result
            # ... and swallow that exception silently.
        # Other exceptions will be handled as normal.

        # NOTE that this releases a savepoint but does not commit() the main
        # session; the caller must still do that.

        # The read-only situation REQUIRES that the session itself is
        # read-only.

    def dialog_to_object(self, obj: object) -> None:
        """
        The class using the mixin must override this to write information
        from the dialogue box to the SQLAlchemy ORM object. It should
        raise an exception if validation fails. (This class isn't fussy about
        which exception that is; it checks for :exc:`Exception`.)
        """
        raise NotImplementedError


class TransactionalDialog(QDialog):
    """
    Dialog for transactional database processing that is simpler than
    :class:`TransactionalEditDialogMixin`.

    - Just overrides ``exec_()``.
    - Wraps the editing in a ``SAVEPOINT`` transaction.
    - The caller must still ``commit()`` afterwards, but any rollbacks are
      automatic.
    - The read-only situation REQUIRES that the session itself is read-only.
    """

    def __init__(self, session: Session, readonly: bool = False,
                 parent: QObject = None, **kwargs) -> None:
        """
        Args:
            session: SQLAlchemy :class:`Session`
            readonly: is this being used in a read-only situation?
            parent: optional parent :class:`QObject`
            kwargs: additional parameters to superclass
        """
        super().__init__(parent=parent, **kwargs)
        self.session = session
        self.readonly = readonly

    # noinspection PyArgumentList
    @pyqtSlot()
    def exec_(self, *args, **kwargs):
        """
        Runs the dialogue.
        """
        if self.readonly:
            return super().exec_(*args, **kwargs)  # enforces modal
        result = None
        try:
            with self.session.begin_nested():
                result = super().exec_(*args, **kwargs)  # enforces modal
                if result == QDialog.Accepted:
                    return result
                else:
                    raise EditCancelledException()
        except EditCancelledException:
            log.debug("Dialog changes have been rolled back.")
            return result
            # ... and swallow that exception silently.
        # Other exceptions will be handled as normal.


# =============================================================================
# Common mixins for models/views handling transaction-isolated database objects
# =============================================================================

class DatabaseModelMixin(object):
    """
    Mixin to provide functions that operate on items within a Qt
    Model and talk to an underlying SQLAlchemy database session.

    Typically mixed in like this:

    .. code-block:: python

        class MyListModel(QAbstractListModel, DatabaseModelMixin):
            pass

    """
    def __init__(self,
                 session: Session,
                 listdata: List[Any],
                 **kwargs) -> None:
        """
        Args:
            session: SQLAlchemy :class:`Session`
            listdata: data; a collection of SQLAlchemy ORM objects in a format
                that behaves like a list
            kwargs: additional parameters for superclass (required for mixins)
        """
        super().__init__(**kwargs)
        self.session = session
        self.listdata = listdata
        log.debug("DatabaseModelMixin: session={}".format(repr(session)))

    def get_object(self, index: int) -> Any:
        """
        Args:
            index: integer index

        Returns:
            ORM object at the index, or ``None`` if the index is out of bounds

        """
        if index is None or not (0 <= index < len(self.listdata)):
            # log.debug("DatabaseModelMixin.get_object: bad index")
            return None
        return self.listdata[index]

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def item_deletable(self, rowindex: int) -> bool:
        """
        Override this if you need to prevent rows being deleted.
        """
        return True

    def delete_item(self, row_index: bool,
                    delete_from_session: bool = True) -> None:
        """
        Deletes an item from the collection (and optionally from the
        SQLAlchemy session).

        Args:
            row_index: index
            delete_from_session: also delete the ORM object from the SQLAlchemy
                session? Default is ``True``.

        Raises:
            ValueError: if index invalid

        """
        if row_index < 0 or row_index >= len(self.listdata):
            raise ValueError("Invalid index {}".format(row_index))
        if delete_from_session:
            obj = self.listdata[row_index]
            self.session.delete(obj)
        # noinspection PyUnresolvedReferences
        self.beginRemoveRows(QModelIndex(), row_index, row_index)
        del self.listdata[row_index]
        # noinspection PyUnresolvedReferences
        self.endRemoveRows()

    def insert_at_index(self, obj: object, index: int = None,
                        add_to_session: bool = True,
                        flush: bool = True) -> None:
        """
        Inserts an ORM object into the data list.

        Args:
            obj: SQLAlchemy ORM object to insert
            index: add it at this index location; specifying ``None`` adds it
                at the end of the list
            add_to_session: also add the object to the SQLAlchemy session?
                Default is ``True``.
            flush: flush the SQLAlchemy session after adding the object?
                Only applicable if ``add_to_session`` is true.

        Raises:
            ValueError: if index invalid

        """
        if index is None:
            index = len(self.listdata)
        if index < 0 or index > len(self.listdata):  # NB permits "== len"
            raise ValueError("Bad index")
        if add_to_session:
            self.session.add(obj)
            if flush:
                self.session.flush()
        # http://stackoverflow.com/questions/4702972
        # noinspection PyUnresolvedReferences
        self.beginInsertRows(QModelIndex(), 0, 0)
        self.listdata.insert(index, obj)
        # noinspection PyUnresolvedReferences
        self.endInsertRows()

    def move_up(self, index: int) -> None:
        """
        Moves an object up one place in the list (from ``index`` to ``index -
        1``).

        Args:
            index: index of the object to move

        Raises:
            ValueError: if index invalid

        """
        if index is None or index < 0 or index >= len(self.listdata):
            raise ValueError("Bad index")
        if index == 0:
            return
        x = self.listdata  # shorter name!
        x[index - 1], x[index] = x[index], x[index - 1]
        # noinspection PyUnresolvedReferences
        self.dataChanged.emit(QModelIndex(), QModelIndex())

    def move_down(self, index: int) -> None:
        """
        Moves an object down one place in the list (from ``index`` to ``index +
        1``).

        Args:
            index: index of the object to move

        Raises:
            ValueError: if index invalid

        """
        if index is None or index < 0 or index >= len(self.listdata):
            raise ValueError("Bad index")
        if index == len(self.listdata) - 1:
            return
        x = self.listdata  # shorter name!
        x[index + 1], x[index] = x[index], x[index + 1]
        # noinspection PyUnresolvedReferences
        self.dataChanged.emit(QModelIndex(), QModelIndex())


class ViewAssistMixin(object):
    """
    Mixin to add SQLAlchemy database-handling functions to a
    :class:`ViewAssistMixin`.

    Typically used like this:

    .. code-block:: python

        class MyListView(QListView, ViewAssistMixin):
            pass

    Signals:

    - ``selection_changed(QItemSelection, QItemSelection)``
    - ``selected_maydelete(bool, bool)``

    """
    selection_changed = pyqtSignal(QItemSelection, QItemSelection)
    # ... selected (set), deselected (set)
    selected_maydelete = pyqtSignal(bool, bool)
    # ... selected

    # -------------------------------------------------------------------------
    # Initialization and setting data (model)
    # -------------------------------------------------------------------------

    def __init__(self, session: Session,
                 modal_dialog_class: Type[TransactionalEditDialogMixin],
                 readonly: bool = False,
                 *args,
                 **kwargs) -> None:
        """
        Args:
            session: SQLAlchemy :class:`Session`
            modal_dialog_class: class that is a subclass of
                :class:`TransactionalEditDialogMixin`
            readonly: read-only view?
            kwargs: additional parameters for superclass (required for mixins)
        """
        super().__init__(*args, **kwargs)
        self.session = session
        self.modal_dialog_class = modal_dialog_class
        self.readonly = readonly
        self.selection_model = None

    def set_model_common(self,
                         model: QAbstractListModel,
                         listview_base_class: Type[QListView]) -> None:
        """
        Helper function to set up a Qt model.

        Args:
            model: instance of the Qt model
            listview_base_class: class being used as the Qt view
        """
        if self.selection_model:
            # noinspection PyUnresolvedReferences
            self.selection_model.selectionChanged.disconnect()
        # noinspection PyCallByClass,PyTypeChecker
        listview_base_class.setModel(self, model)
        self.selection_model = QItemSelectionModel(model)
        # noinspection PyUnresolvedReferences
        self.selection_model.selectionChanged.connect(self._selection_changed)
        # noinspection PyUnresolvedReferences
        self.setSelectionModel(self.selection_model)

    # -------------------------------------------------------------------------
    # Selection
    # -------------------------------------------------------------------------

    def clear_selection(self) -> None:
        """
        Clears any selection.
        """
        # log.debug("GenericAttrTableView.clear_selection")
        if not self.selection_model:
            return
        self.selection_model.clearSelection()

    def get_selected_row_index(self) -> Optional[int]:
        """
        Gets the index of the currently selected row.

        Returns:
            index, or ``None``

        """
        selected_modelindex = self.get_selected_modelindex()
        if selected_modelindex is None:
            return None
        return selected_modelindex.row()

    def is_selected(self) -> bool:
        """
        Is a row currently selected?
        """
        row_index = self.get_selected_row_index()
        return row_index is not None

    def get_selected_object(self) -> Optional[object]:
        """
        Returns the SQLAlchemy ORM object that's currently selected, or
        ``None``.
        """
        index = self.get_selected_row_index()
        if index is None:
            return None
        # noinspection PyUnresolvedReferences
        model = self.model()
        if model is None:
            return None
        return model.get_object(index)

    def get_selected_modelindex(self) -> Optional[QModelIndex]:
        """
        Returns the :class:`QModelIndex` of the currently selected row, or
        ``None``.

        Should be overridden in derived classes.
        """
        raise NotImplementedError()

    def go_to(self, row: Optional[int]) -> None:
        """
        Makes a specific row (by index) the currently selected row.

        Args:
            row: row index, or ``None`` to select the last row if there is one
        """
        # noinspection PyUnresolvedReferences
        model = self.model()
        if row is None:
            # Go to the end.
            nrows = model.rowCount()
            if nrows == 0:
                return
            row = nrows - 1
        modelindex = model.index(row, 0)  # second parameter is column
        # noinspection PyUnresolvedReferences
        self.setCurrentIndex(modelindex)

    def _selection_changed(self,
                           selected: QItemSelection,
                           deselected: QItemSelection) -> None:
        """
        Receives an event when the model's selection is changed.
        """
        self.selection_changed.emit(selected, deselected)
        selected_model_indexes = selected.indexes()
        selected_row_indexes = [mi.row() for mi in selected_model_indexes]
        is_selected = bool(selected_row_indexes)
        # noinspection PyUnresolvedReferences
        model = self.model()
        may_delete = is_selected and all(
            [model.item_deletable(ri) for ri in selected_row_indexes])
        self.selected_maydelete.emit(is_selected, may_delete)

    def get_n_rows(self) -> int:
        """
        Returns:
            the number of rows (items) present
        """
        # noinspection PyUnresolvedReferences
        model = self.model()
        return model.rowCount()

    # -------------------------------------------------------------------------
    # Add
    # -------------------------------------------------------------------------

    def insert_at_index(self, obj: object, index: int = None,
                        add_to_session: bool = True,
                        flush: bool = True) -> None:
        """
        Insert an SQLAlchemy ORM object into the model at a specific location
        (and, optionally, into the SQLAlchemy session).

        Args:
            obj: SQLAlchemy ORM object to insert
            index: index to insert at; ``None`` for end, ``0`` for start
            add_to_session: also add the object to the SQLAlchemy session?
                Default is ``True``.
            flush: flush the SQLAlchemy session after adding the object?
                Only applicable if ``add_to_session`` is true.
        """
        # noinspection PyUnresolvedReferences
        model = self.model()
        model.insert_at_index(obj, index,
                              add_to_session=add_to_session, flush=flush)
        self.go_to(index)

    def insert_at_start(self, obj: object,
                        add_to_session: bool = True,
                        flush: bool = True) -> None:
        """
        Insert a SQLAlchemy ORM object into the model at the start of the list
        (and, optionally, into the SQLAlchemy session).

        Args:
            obj: SQLAlchemy ORM object to insert
            add_to_session: also add the object to the SQLAlchemy session?
                Default is ``True``.
            flush: flush the SQLAlchemy session after adding the object?
                Only applicable if ``add_to_session`` is true.
        """
        self.insert_at_index(obj, 0,
                             add_to_session=add_to_session, flush=flush)

    def insert_at_end(self, obj: object,
                      add_to_session: bool = True,
                      flush: bool = True) -> None:
        """
        Insert a SQLAlchemy ORM object into the model at the end of the list
        (and, optionally, into the SQLAlchemy session).

        Args:
            obj: SQLAlchemy ORM object to insert
            add_to_session: also add the object to the SQLAlchemy session?
                Default is ``True``.
            flush: flush the SQLAlchemy session after adding the object?
                Only applicable if ``add_to_session`` is true.
        """
        self.insert_at_index(obj, None,
                             add_to_session=add_to_session, flush=flush)

    def add_in_nested_transaction(self, new_object: object,
                                  at_index: int = None) -> Optional[int]:
        """
        Starts an SQLAlchemy nested transaction (which uses ``SAVEPOINT`` SQL);
        adds the new object into the session; edits the object. If the editing
        is cancelled, cancel the addition. Otherwise, the object is added to
        the session (in a nested transaction that might be cancelled by a
        caller) and to the model/list.

        Args:
            new_object: SQLAlchemy ORM object to insert
            at_index: add it at this index location; specifying ``None`` (the
                default) adds it at the end of the list; ``0`` is the start
        """
        if self.readonly:
            log.warning("Can't add; readonly")
            return
        result = None
        try:
            with self.session.begin_nested():
                self.session.add(new_object)
                # noinspection PyArgumentList
                win = self.modal_dialog_class(self.session, new_object)
                result = win.edit_in_nested_transaction()
                if result != QDialog.Accepted:
                    raise EditCancelledException()
                self.insert_at_index(new_object, at_index,
                                     add_to_session=False)
                return result
        except EditCancelledException:
            log.debug("Add operation has been rolled back.")
            return result

    # -------------------------------------------------------------------------
    # Remove
    # -------------------------------------------------------------------------

    def remove_selected(self, delete_from_session: bool = True) -> None:
        """
        Remove the currently selected SQLAlchemy ORM object from the list.

        Args:
            delete_from_session: also delete it from the SQLAlchemy session?
                (default: ``True``)
        """
        row_index = self.get_selected_row_index()
        self.remove_by_index(row_index,
                             delete_from_session=delete_from_session)

    def remove_by_index(self, row_index: int,
                        delete_from_session: bool = True) -> None:
        """
        Remove a specified SQLAlchemy ORM object from the list.

        Args:
            row_index: index of object to remove
            delete_from_session: also delete it from the SQLAlchemy session?
                (default: ``True``)
        """
        if row_index is None:
            return
        # noinspection PyUnresolvedReferences
        model = self.model()
        model.delete_item(row_index, delete_from_session=delete_from_session)

    # -------------------------------------------------------------------------
    # Move
    # -------------------------------------------------------------------------

    def move_selected_up(self) -> None:
        """
        Moves the selected object up one place in the list.
        """
        row_index = self.get_selected_row_index()
        if row_index is None or row_index == 0:
            return
        # noinspection PyUnresolvedReferences
        model = self.model()
        model.move_up(row_index)
        self.go_to(row_index - 1)

    def move_selected_down(self) -> None:
        """
        Moves the selected object down one place in the list.
        """
        row_index = self.get_selected_row_index()
        if row_index is None or row_index == self.get_n_rows() - 1:
            return
        # noinspection PyUnresolvedReferences
        model = self.model()
        model.move_down(row_index)
        self.go_to(row_index + 1)

    # -------------------------------------------------------------------------
    # Edit
    # -------------------------------------------------------------------------

    # noinspection PyUnusedLocal
    def edit(self,
             index: QModelIndex,
             trigger: QAbstractItemView.EditTrigger,
             event: QEvent) -> bool:
        """
        Edits the specified object.

        Overrides :func:`QAbstractItemView::edit`; see
        http://doc.qt.io/qt-5/qabstractitemview.html#edit-1.

        Args:
            index: :class:`QModelIndex` of the object to edit
            trigger: action that caused the editing process
            event: associated :class:`QEvent`

        Returns:
            ``True`` if the view's ``State`` is now ``EditingState``;
            otherwise ``False``

        """
        if trigger != QAbstractItemView.DoubleClicked:
            return False
        self.edit_by_modelindex(index)
        return False

    def edit_by_modelindex(self, index: QModelIndex,
                           readonly: bool = None) -> None:
        """
        Edits the specified object.

        Args:
            index: :class:`QModelIndex` of the object to edit
            readonly: read-only view? If ``None`` (the default), uses the
                setting from ``self``.
        """
        if index is None:
            return
        if readonly is None:
            readonly = self.readonly
        # noinspection PyUnresolvedReferences
        model = self.model()
        item = model.listdata[index.row()]
        # noinspection PyArgumentList
        win = self.modal_dialog_class(self.session, item, readonly=readonly)
        win.edit_in_nested_transaction()

    def edit_selected(self, readonly: bool = None) -> None:
        """
        Edits the currently selected object.

        Args:
            readonly: read-only view? If ``None`` (the default), uses the
                setting from ``self``.
        """
        selected_modelindex = self.get_selected_modelindex()
        self.edit_by_modelindex(selected_modelindex, readonly=readonly)


# =============================================================================
# Framework for list boxes
# =============================================================================

# For stuff where we want to display a list (e.g. of strings) and edit items
# with a dialog:
# - view is a QListView (itself a subclass of QAbstractItemView):
#   ... or perhaps QAbstractItemView directly
#   http://doc.qt.io/qt-5/qlistview.html#details
#   http://doc.qt.io/qt-4.8/qabstractitemview.html
# - model is perhaps a subclass of QAbstractListModel:
#   http://doc.qt.io/qt-5/qabstractlistmodel.html#details
#
# Custom editing:
# - ?change the delegate?
#   http://www.saltycrane.com/blog/2008/01/pyqt4-qitemdelegate-example-with/
#   ... no, can't be a modal dialog
#       http://stackoverflow.com/questions/27180602
#       https://bugreports.qt.io/browse/QTBUG-11908
# - ?override the edit function of the view?
#   http://stackoverflow.com/questions/27180602
#   - the edit function is part of QAbstractItemView
#     http://doc.qt.io/qt-4.8/qabstractitemview.html#public-slots
#   - but then, with the index (which is a QModelIndex, not an integer), we
#     have to fetch the model with self.model(), then operate on it somehow;
#     noting that a QModelIndex fetches the data from its model using the
#     data() function, which we are likely to have bastardized to fit into a
#     string. So this is all a bit convoluted.
#   - Ah! Not if we use row() then access the raw data directly from our mdoel.


class GenericListModel(QAbstractListModel, DatabaseModelMixin):
    """
    Takes a list and provides a view on it using :func:`str`. That is, for
    a list of object ``[a, b, c]``, it displays a list view with items (rows)
    like this:

        +-------------+
        | ``str(a)``  |
        +-------------+
        | ``str(b)``  |
        +-------------+
        | ``str(c)``  |
        +-------------+

    - Note that it MODIFIES THE LIST PASSED TO IT.
    """
    def __init__(self, data, session: Session, parent: QObject = None,
                 **kwargs) -> None:
        super().__init__(session=session, listdata=data, parent=parent,
                         **kwargs)

    # noinspection PyUnusedLocal, PyPep8Naming
    def rowCount(self, parent: QModelIndex = QModelIndex(),
                 *args, **kwargs) -> int:
        """
        Counts the number of rows.

        Overrides :func:`QAbstractListModel.rowCount`; see
        http://doc.qt.io/qt-5/qabstractitemmodel.html.

        Args:
            parent: parent object, specified by :class:`QModelIndex`
            args: unnecessary? Certainly unused.
            kwargs: unnecessary? Certainly unused.

        Returns:
            In the Qt original: "number of rows under the given parent.
            When the parent is valid... the number of children of ``parent``."
            Here: the number of objects in the list.

        """
        return len(self.listdata)

    def data(self, index: QModelIndex,
             role: int = Qt.DisplayRole) -> Optional[str]:
        """
        Returns the data for a given row (in this case as a string).

        Overrides :func:`QAbstractListModel.data`; see
        http://doc.qt.io/qt-5/qabstractitemmodel.html.

        Args:
            index: :class:`QModelIndex`, which specifies the row number
            role: a way of specifying the type of view on the data; here,
                we only accept ``Qt.DisplayRole``

        Returns:
            string representation of the object, or ``None``

        """
        if index.isValid() and role == Qt.DisplayRole:
            return str(self.listdata[index.row()])
        return None


class ModalEditListView(QListView, ViewAssistMixin):
    """
    A version of :class:`QListView` that supports SQLAlchemy handling of its
    objects.
    """

    # -------------------------------------------------------------------------
    # Initialization and setting data (model)
    # -------------------------------------------------------------------------

    def __init__(self,
                 session: Session,
                 modal_dialog_class: Type[TransactionalEditDialogMixin],
                 *args,
                 readonly: bool = False,
                 **kwargs) -> None:
        """

        Args:
            session: SQLAlchemy :class:`Session`
            modal_dialog_class: class that is a subclass of
                :class:`TransactionalEditDialogMixin`
            readonly: read-only view?
            args: positional arguments to superclass
            kwargs: keyword arguments to superclass
        """
        self.readonly = readonly
        super().__init__(session=session,
                         modal_dialog_class=modal_dialog_class,
                         readonly=self.readonly,
                         *args, **kwargs)
        # self.setEditTriggers(QAbstractItemView.DoubleClicked)
        # ... probably only relevant if we do NOT override edit().
        # Being able to select a single row is the default.
        # Otherwise see SelectionBehavior and SelectionMode.

    # noinspection PyPep8Naming
    def setModel(self, model: QAbstractListModel) -> None:
        """
        Qt override to set the model used by this view.

        Args:
            model: instance of the model
        """
        self.set_model_common(model, QListView)

    # -------------------------------------------------------------------------
    # Selection
    # -------------------------------------------------------------------------

    def get_selected_modelindex(self) -> Optional[QModelIndex]:
        """
        Gets the model index of the selected item.

        Returns:
            a :class:`QModelIndex` or ``None``

        """
        selected_indexes = self.selectedIndexes()
        if not selected_indexes or len(selected_indexes) > 1:
            # log.warning("get_selected_modelindex: 0 or >1 selected")
            return None
        return selected_indexes[0]


# =============================================================================
# Framework for tables
# =============================================================================

class GenericAttrTableModel(QAbstractTableModel, DatabaseModelMixin):
    """
    Takes a list of objects and a list of column headers;
    provides a view on it using func:`str`. That is, for a list of objects
    ``[a, b, c]`` and a list of headers ``["h1", "h2", "h3"]``, it provides
    a table view like

        =============== =============== =================
        h1              h2              h3
        =============== =============== =================
        ``str(a.h1)``   ``str(a.h2)``   ``str(a.h3)``
        ``str(b.h1)``   ``str(b.h2)``   ``str(b.h3)``
        ``str(c.h1)``   ``str(c.h2)``   ``str(c.h3)``
        =============== =============== =================

    - Note that it MODIFIES THE LIST PASSED TO IT.

    - Sorting: consider :class:`QSortFilterProxyModel`... but not clear that
      can do arbitrary column sorts, since its sorting is via its
      ``lessThan()`` function.

    - The tricky part is keeping selections persistent after sorting.
      Not achieved yet. Simpler to wipe the selections.
    """
    # http://doc.qt.io/qt-4.8/qabstracttablemodel.html

    def __init__(self,
                 data: List[Any],
                 header: List[Tuple[str, str]],
                 session: Session,
                 default_sort_column_name: str = None,
                 default_sort_order: int = Qt.AscendingOrder,
                 deletable: bool = True,
                 parent: QObject = None,
                 **kwargs) -> None:
        """
        Args:
            data: data; a collection of SQLAlchemy ORM objects in a format
                that behaves like a list
            header: list of ``(colname, attr_or_func)`` tuples. The first part,
                ``colname``, is displayed to the user. The second part,
                ``attr_or_func``, is used to retrieve data. For each object
                ``obj``, the view will call ``thing = getattr(obj,
                attr_or_func)``. If ``thing`` is callable (i.e. is a member
                function), the view will display ``str(thing())``; otherwise,
                it will display ``str(thing)``.
            session: SQLAlchemy :class:`Session`
            default_sort_column_name: column to sort by to begin with, or
                ``None`` to respect the original order of ``data``
            default_sort_order: default sort order (default is ascending
                order)
            deletable: may the user delete objects from the collection?
            parent: parent (owning) :class:`QObject`
            kwargs: additional parameters for superclass (required for mixins)
        """
        super().__init__(session=session,
                         listdata=data,
                         parent=parent,
                         **kwargs)
        self.header_display = [x[0] for x in header]
        self.header_attr = [x[1] for x in header]
        self.deletable = deletable
        self.default_sort_column_num = None
        self.default_sort_order = default_sort_order
        if default_sort_column_name is not None:
            self.default_sort_column_num = self.header_attr.index(
                default_sort_column_name)
            # ... will raise an exception if bad
            self.sort(self.default_sort_column_num, default_sort_order)

    def get_default_sort(self) -> Tuple[int, int]:
        """
        Returns:
            ``(default_sort_column_number, default_sort_order)``
            where the column number is zero-based and the sort order is
            as per :func:`__init__`
        """
        return self.default_sort_column_num, self.default_sort_order

    # noinspection PyUnusedLocal, PyPep8Naming
    def rowCount(self, parent: QModelIndex = QModelIndex(),
                 *args, **kwargs):
        """
        Counts the number of rows.

        Overrides :func:`QAbstractTableModel.rowCount`; see
        http://doc.qt.io/qt-5/qabstractitemmodel.html.

        Args:
            parent: parent object, specified by :class:`QModelIndex`
            args: unnecessary? Certainly unused.
            kwargs: unnecessary? Certainly unused.

        Returns:
            In the Qt original: "number of rows under the given parent.
            When the parent is valid... the number of children of ``parent``."
            Here: the number of objects in the list.

        """
        return len(self.listdata)

    # noinspection PyUnusedLocal, PyPep8Naming
    def columnCount(self, parent: QModelIndex = QModelIndex(),
                    *args, **kwargs):
        """
        Qt override.

        Args:
            parent: parent object, specified by :class:`QModelIndex`
            args: unnecessary? Certainly unused.
            kwargs: unnecessary? Certainly unused.

        Returns:
            number of columns

        """
        return len(self.header_attr)

    def data(self, index: QModelIndex,
             role: int = Qt.DisplayRole) -> Optional[str]:
        """
        Returns the data for a given row/column (in this case as a string).

        Overrides :func:`QAbstractTableModel.data`; see
        http://doc.qt.io/qt-5/qabstractitemmodel.html.

        Args:
            index: :class:`QModelIndex`, which specifies the row/column
                number
            role: a way of specifying the type of view on the data; here,
                we only accept ``Qt.DisplayRole``

        Returns:
            string representation of the relevant attribute (or member function
            result) for the relevant SQLAlchemy ORM object, or ``None``

        """
        if index.isValid() and role == Qt.DisplayRole:
            obj = self.listdata[index.row()]
            colname = self.header_attr[index.column()]
            thing = getattr(obj, colname)
            if callable(thing):
                return str(thing())
            else:
                return str(thing)
        return None

    # noinspection PyPep8Naming
    def headerData(self, col: int, orientation: int,
                   role: int = Qt.DisplayRole) -> Optional[str]:
        """
        Qt override.

        Returns the column heading for a particular column.

        Args:
            col: column number
            orientation: required to be ``Qt.Horizontal``
            role: required to be ``Qt.DisplayRole``

        Returns:
            column header string, or ``None``

        """
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header_display[col]
        return None

    def sort(self, col: int, order: int = Qt.AscendingOrder) -> None:
        """
        Sort table on a specified column.

        Args:
            col: column number
            order: sort order (e.g. ascending order)
        """
        # log.debug("GenericAttrTableModel.sort")
        if not self.listdata:
            return
        # noinspection PyUnresolvedReferences
        self.layoutAboutToBeChanged.emit()
        colname = self.header_attr[col]
        isfunc = callable(getattr(self.listdata[0], colname))
        if isfunc:
            self.listdata = sorted(
                self.listdata,
                key=methodcaller_nonesort(colname))
        else:
            self.listdata = sorted(self.listdata,
                                   key=attrgetter_nonesort(colname))
        if order == Qt.DescendingOrder:
            self.listdata.reverse()
        # noinspection PyUnresolvedReferences
        self.layoutChanged.emit()


class GenericAttrTableView(QTableView, ViewAssistMixin):
    """
    Provides a :class:`QTableView` view on SQLAlchemy data.

    Signals:

    - ``selection_changed(QItemSelection, QItemSelection)``

    """
    selection_changed = pyqtSignal(QItemSelection, QItemSelection)

    # -------------------------------------------------------------------------
    # Initialization and setting data (model)
    # -------------------------------------------------------------------------

    def __init__(self,
                 session: Session,
                 modal_dialog_class,
                 parent: QObject = None,
                 sortable: bool = True,
                 stretch_last_section: bool = True,
                 readonly: bool = False,
                 **kwargs) -> None:
        """
        Args:
            session: SQLAlchemy :class:`Session`
            modal_dialog_class: class that is a subclass of
                :class:`TransactionalEditDialogMixin`
            parent: parent (owning) :class:`QObject`
            sortable: should we sort the data?
            stretch_last_section: stretch the last column (section)
                horizontally?
            readonly: read-only view?
            kwargs: additional parameters for superclass (required for mixins)
        """
        super().__init__(session=session,
                         modal_dialog_class=modal_dialog_class,
                         readonly=readonly,
                         parent=parent,
                         **kwargs)
        self.sortable = sortable
        self.sizing_done = False
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSortingEnabled(sortable)
        hh = self.horizontalHeader()
        # hh.setClickable(sortable)  # old, removed in favour of:
        hh.setSectionsClickable(sortable)  # Qt 5
        hh.sectionClicked.connect(self.clear_selection)
        # ... clear selection when we sort
        hh.setSortIndicatorShown(sortable)
        hh.setStretchLastSection(stretch_last_section)

    # noinspection PyPep8Naming
    def setModel(self, model: QAbstractTableModel) -> None:
        """
        Qt override to set the model used by this view.

        Args:
            model: instance of the model
        """
        self.set_model_common(model, QTableView)
        if self.sortable:
            colnum, order = model.get_default_sort()
            hh = self.horizontalHeader()
            hh.setSortIndicator(colnum, order)
        self.refresh_sizing()

    # -------------------------------------------------------------------------
    # Visuals
    # -------------------------------------------------------------------------

    def refresh_sizing(self) -> None:
        """
        Ask the view to resize its rows/columns to fit its data.
        """
        self.sizing_done = False
        self.resize()

    def resize(self) -> None:
        """
        Resize all rows to have the correct height, and its columns to the
        correct width.
        """
        #
        if self.sizing_done:
            return
        self.resizeRowsToContents()
        self.resizeColumnsToContents()
        self.sizing_done = True

    # -------------------------------------------------------------------------
    # Selection
    # -------------------------------------------------------------------------

    def get_selected_modelindex(self) -> Optional[QModelIndex]:
        """
        Gets the model index of the selected item.

        Returns:
            a :class:`QModelIndex` or ``None``

        """
        # Here, self.selectedIndexes() returns a list of (row, col)
        # tuple indexes, which is not what we want.
        # So we use the selectedRows() method of the selection model.
        if self.selection_model is None:
            return None
        selected_indexes = self.selection_model.selectedRows()
        # log.debug("selected_indexes: {}".format(selected_indexes))
        if not selected_indexes or len(selected_indexes) > 1:
            # log.warning("get_selected_modelindex: 0 or >1 selected")
            return None
        return selected_indexes[0]


# =============================================================================
# RadioGroup
# =============================================================================

class RadioGroup(object):
    """
    Framework for radio buttons.
    """

    def __init__(self,
                 value_text_tuples: Iterable[Tuple[str, Any]],
                 default: Any = None) -> None:
        """
        Args:
            value_text_tuples: list of ``(value, text)`` tuples, where
                ``value`` is the value stored to Python object and ``text``
                is the text shown to the user
            default: default value
        """
        # There's no reason for the caller to care about the internal IDs
        # we use. So let's make them up here as positive integers.
        self.default_value = default
        if not value_text_tuples:
            raise ValueError("No values passed to RadioGroup")
        if contains_duplicates([x[0] for x in value_text_tuples]):
            raise ValueError("Duplicate values passed to RadioGroup")
        possible_values = [x[0] for x in value_text_tuples]
        if self.default_value not in possible_values:
            self.default_value = possible_values[0]
        self.bg = QButtonGroup()  # exclusive by default
        self.buttons = []
        self.map_id_to_value = {}
        self.map_value_to_button = {}
        for i, (value, text) in enumerate(value_text_tuples):
            id_ = i + 1  # start with 1
            button = QRadioButton(text)
            self.bg.addButton(button, id_)
            self.buttons.append(button)
            self.map_id_to_value[id_] = value
            self.map_value_to_button[value] = button

    def get_value(self) -> Any:
        """
        Returns:
            the value of the currently selected radio button, or ``None`` if
            none is selected
        """
        buttongroup_id = self.bg.checkedId()
        if buttongroup_id == NOTHING_SELECTED:
            return None
        return self.map_id_to_value[buttongroup_id]

    def set_value(self, value: Any) -> None:
        """
        Set the radio group to the specified value.
        """
        if value not in self.map_value_to_button:
            value = self.default_value
        button = self.map_value_to_button[value]
        button.setChecked(True)

    def add_buttons_to_layout(self, layout: QLayout) -> None:
        """
        Adds its button widgets to the specified Qt layout.
        """
        for button in self.buttons:
            layout.addWidget(button)


# =============================================================================
# Garbage collector
# =============================================================================

class GarbageCollector(QObject):
    """
    Disable automatic garbage collection and instead collect manually
    every INTERVAL milliseconds.

    This is done to ensure that garbage collection only happens in the GUI
    thread, as otherwise Qt can crash.

    See:
    
    - https://riverbankcomputing.com/pipermail/pyqt/2011-August/030378.html
    - http://pydev.blogspot.co.uk/2014/03/should-python-garbage-collector-be.html
    - https://bugreports.qt.io/browse/PYSIDE-79
    
    """  # noqa

    def __init__(self, parent: QObject, debug: bool = False,
                 interval_ms=10000) -> None:
        """

        Args:
            parent: parent :class:`QObject`
            debug: be verbose about garbage collection
            interval_ms: period/interval (in ms) at which to perform garbage
                collection
        """
        super().__init__(parent)
        self.debug = debug
        self.interval_ms = interval_ms

        self.timer = QTimer(self)
        # noinspection PyUnresolvedReferences
        self.timer.timeout.connect(self.check)

        self.threshold = gc.get_threshold()
        gc.disable()
        self.timer.start(self.interval_ms)

    def check(self) -> None:
        """
        Check if garbage collection should happen, and if it should, do it.
        """
        # return self.debug_cycles()  # uncomment to just debug cycles
        l0, l1, l2 = gc.get_count()
        if self.debug:
            log.debug('GarbageCollector.check called: '
                      'l0={}, l1={}, l2={}'.format(l0, l1, l2))
        if l0 > self.threshold[0]:
            num = gc.collect(generation=0)
            if self.debug:
                log.debug('collecting generation 0; found '
                          '{} unreachable'.format(num))
            if l1 > self.threshold[1]:
                num = gc.collect(generation=1)
                if self.debug:
                    log.debug('collecting generation 1; found '
                              '{} unreachable'.format(num))
                if l2 > self.threshold[2]:
                    num = gc.collect(generation=2)
                    if self.debug:
                        log.debug('collecting generation 2; found '
                                  '{} unreachable'.format(num))

    @staticmethod
    def debug_cycles() -> None:
        """
        Collect garbage and print what was collected.
        """
        gc.set_debug(gc.DEBUG_SAVEALL)
        gc.collect()
        for obj in gc.garbage:
            print(obj, repr(obj), type(obj))


# =============================================================================
# Decorator to stop whole program on exceptions (use for threaded slots)
# =============================================================================

def exit_on_exception(func):
    """
    Decorator to stop whole program on exceptions (use for threaded slots).

    See

    - http://stackoverflow.com/questions/18740884
    - http://stackoverflow.com/questions/308999/what-does-functools-wraps-do

    Args:
        func: the function to decorate

    Returns:
        the decorated function

    """

    @wraps(func)
    def with_exit_on_exception(*args, **kwargs):
        # noinspection PyBroadException,PyPep8
        try:
            return func(*args, **kwargs)
        except:
            log.critical("=" * 79)
            log.critical(
                "Uncaught exception in slot, within thread: {}".format(
                    threading.current_thread().name))
            log.critical("-" * 79)
            log.critical(traceback.format_exc())
            log.critical("-" * 79)
            log.critical("For function {},".format(func.__name__))
            log.critical("args: {}".format(", ".join(repr(a) for a in args)))
            log.critical("kwargs: {}".format(kwargs))
            log.critical("=" * 79)
            sys.exit(1)
    return with_exit_on_exception


# =============================================================================
# Run a GUI, given a base window.
# =============================================================================

def run_gui(qt_app: QApplication, win: QDialog) -> int:
    """
    Run a GUI, given a base window.

    Args:
        qt_app: Qt application
        win: Qt dialogue window

    Returns:
        exit code

    """
    win.show()
    return qt_app.exec_()
