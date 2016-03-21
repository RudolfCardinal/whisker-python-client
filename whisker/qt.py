#!/usr/bin/env python
# whisker/qt.py
# Copyright (c) Rudolf Cardinal (rudolf@pobox.com).
# See LICENSE for details.


from functools import wraps
import logging
import sys
import threading
import traceback

from PySide.QtCore import (
    QAbstractListModel,
    QAbstractTableModel,
    QModelIndex,
    Qt,
    # QVariant,  # non-existent in PySide?
    Signal,
    Slot,
)
from PySide.QtGui import (
    QAbstractItemView,
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QItemSelection,
    QItemSelectionModel,
    QListView,
    QMessageBox,
    QRadioButton,
    QTableView,
    QVBoxLayout,
)

from whisker.lang import (
    attrgetter_nonesort,
    contains_duplicates,
    get_caller_name,
    methodcaller_nonesort,
)

log = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

NOTHING_SELECTED = -1  # e.g. http://doc.qt.io/qt-4.8/qbuttongroup.html#id


# =============================================================================
# Exceptions
# =============================================================================

class ValidationError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return self.message


class EditCancelledException(Exception):
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet(GROUPBOX_STYLESHEET)


# =============================================================================
# StatusMixin - emit status to log and Qt signals
# =============================================================================

class StatusMixin(object):
    """
    Add this to a QObject to provide easy Python logging and Qt signal-based
    status/error messaging.

    Uses the same function names as Python logging, for predictability.
    """
    status_sent = Signal(str, str)
    error_sent = Signal(str, str)

    def __init__(self, name, log, thread_info=True, caller_info=True):
        # Somewhat verbose names to make conflict with a user class unlikely.
        self._statusmixin_name = name
        self._statusmixin_log = log
        self._statusmixin_debug_thread_info = thread_info
        self._statusmixin_debug_caller_info = caller_info

    def _process_status_message(self, msg):
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

    def debug(self, msg):
        self._statusmixin_log.debug(self._process_status_message(msg))

    def critical(self, msg):
        self._statusmixin_log.critical(self._process_status_message(msg))
        self.error_sent.emit(msg, self._statusmixin_name)

    def error(self, msg):
        self._statusmixin_log.error(self._process_status_message(msg))
        self.error_sent.emit(msg, self._statusmixin_name)

    def warning(self, msg):
        # warn() is deprecated; use warning()
        self._statusmixin_log.warning(self._process_status_message(msg))
        self.error_sent.emit(msg, self._statusmixin_name)

    def info(self, msg):
        self._statusmixin_log.info(self._process_status_message(msg))
        self.status_sent.emit(msg, self._statusmixin_name)

    def status(self, msg):
        # Don't just call info, because of the stack-counting thing
        # in _process_status_message
        self._statusmixin_log.info(self._process_status_message(msg))
        self.status_sent.emit(msg, self._statusmixin_name)


# =============================================================================
# Framework for a config-editing dialogue
# =============================================================================

class TransactionalEditDialogMixin(object):
    """
    Mixin for a config-editing dialogue.
    Wraps the editing in a SAVEPOINT transaction.
    The caller must still commit() afterwards, but any rollbacks are automatic.
    """
    ok = Signal()

    def __init__(self, session, obj, layout, readonly=False):
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

        # Pass in data
        self.object_to_dialog(self.obj)

    @Slot()
    def ok_clicked(self):
        try:
            self.dialog_to_object(self.obj)
            self.accept()
        except Exception as e:
            QMessageBox.about(self, "Invalid data", str(e))
            # ... str(e) will be a simple message for ValidationError

    def edit_in_nested_transaction(self):
        """
        Pops up the dialog, allowing editing.
        - Does so within a database transaction.
        - If the user clicks OK *and* the data validates, commits the
          transaction.
        - If the user cancels, rolls back the transaction.
        - We want it nestable, so that the config dialog box can edit part of
          the config, reversibly, without too much faffing around.
        """
        """
        - We could nest using SQLAlchemy's support for nested transactions,
          which works whether or not the database itself supports nested
          transactions via the SAVEPOINT method.
        - With sessions, one must use autocommit=True and the subtransactions
          flag; these are virtual transactions handled by SQLAlchemy.
        - Alternatively one can use begin_nested() or begin(nested=True), which
          uses SAVEPOINT.
        - The following databases support the SAVEPOINT method:
            MySQL with InnoDB
            SQLite, from v3.6.8 (2009)
            PostgreSQL
        - Which is better? The author suggests SAVEPOINT for most applications.
          https://groups.google.com/forum/#!msg/sqlalchemy/CaZyyMx7_8Y/otM0BzDyaigJ  # noqa
          ... including, for subtransactions: "When a rollback is issued, the
          subtransaction will directly roll back the innermost real
          transaction, however each subtransaction still must be explicitly
          rolled back to maintain proper stacking of subtransactions."
          ... i.e. it's not as simple as you might guess.
        - See
          http://docs.sqlalchemy.org/en/latest/core/connections.html
          http://docs.sqlalchemy.org/en/latest/orm/session_transaction.html
          http://stackoverflow.com/questions/2336950/transaction-within-transaction  # noqa
          http://stackoverflow.com/questions/1306869/are-nested-transactions-allowed-in-mysql  # noqa
          https://en.wikipedia.org/wiki/Savepoint
          http://www.sqlite.org/lang_savepoint.html
          http://stackoverflow.com/questions/1654857/nested-transactions-with-sqlalchemy-and-sqlite  # noqa

        - Let's use the SAVEPOINT technique.

        - No. Even this fails:

        with self.session.begin_nested():
            self.config.port = 5000

        - We were aiming for this:

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
            SAVEPOINT sa_savepoint_1
            UPDATE table SET field=?
            RELEASE SAVEPOINT sa_savepoint_1  -- sensible
            ROLLBACK TO SAVEPOINT sa_savepoint_1  -- not sensible
            -- raises sqlite3.OperationalError: no such savepoint: sa_savepoint_1  # noqa

        - May be this bug:
            https://www.mail-archive.com/sqlalchemy@googlegroups.com/msg28381.html  # noqa
            http://bugs.python.org/issue10740
            https://groups.google.com/forum/#!topic/sqlalchemy/1QelhQ19QsE

        - The bugs are detailed in sqlalchemy/dialects/sqlite/pysqlite.py; see
          "Serializable isolation / Savepoints / Transactional DDL"

        - We work around it by adding hooks to the engine as per that advice;
          see db.py

        """
        # A context manager provides cleaner error handling than explicit
        # begin_session() / commit() / rollback() calls.
        # The context manager provided by begin_nested() will commit, or roll
        # back on an exception.
        if self.readonly:
            return self.exec_()  # enforces modal
        try:
            with self.session.begin_nested():
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


class TransactionalDialog(QDialog):
    """
    Simpler dialog for transactional database processing.
    Just overrides exec_().
    Wraps the editing in a SAVEPOINT transaction.
    The caller must still commit() afterwards, but any rollbacks are automatic.
    The read-only situation REQUIRES that the session itself is read-only.
    """

    def __init__(self, session, readonly=False, parent=None):
        super().__init__(parent=parent)
        self.session = session
        self.readonly = readonly

    @Slot()
    def exec_(self, *args, **kwargs):
        if self.readonly:
            return super().exec_(*args, **kwargs)  # enforces modal
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
    def __init__(self, session, parent=None):
        self.session = session
        log.debug("DatabaseModelMixin: session={}".format(repr(session)))

    def get_object(self, index):
        if index is None or not (0 <= index < len(self.listdata)):
            # log.debug("DatabaseModelMixin.get_object: bad index")
            return None
        return self.listdata[index]

    def item_deletable(self, rowindex):
        """Override this if you need to prevent rows being deleted."""
        return True

    def delete_item(self, row_index, delete_from_session=True):
        if row_index < 0 or row_index >= len(self.listdata):
            raise ValueError("Invalid index {}".format(row_index))
        if delete_from_session:
            obj = self.listdata[row_index]
            self.session.delete(obj)
        self.beginRemoveRows(QModelIndex(), row_index, row_index)
        del self.listdata[row_index]
        self.endRemoveRows()

    def insert_at_index(self, obj, index=None, add_to_session=True,
                        flush=True):
        if index is None:
            index = len(self.listdata)
        if index < 0 or index > len(self.listdata):  # NB permits "== len"
            raise ValueError("Bad index")
        if add_to_session:
            self.session.add(obj)
            if flush:
                self.session.flush()
        # http://stackoverflow.com/questions/4702972
        self.beginInsertRows(QModelIndex(), 0, 0)
        self.listdata.insert(index, obj)
        self.endInsertRows()

    def move_up(self, index):
        if index is None or index < 0 or index >= len(self.listdata):
            raise ValueError("Bad index")
        if index == 0:
            return
        x = self.listdata  # shorter name!
        x[index - 1], x[index] = x[index], x[index - 1]
        self.dataChanged.emit(QModelIndex(), QModelIndex())

    def move_down(self, index):
        if index is None or index < 0 or index >= len(self.listdata):
            raise ValueError("Bad index")
        if index == len(self.listdata) - 1:
            return
        x = self.listdata  # shorter name!
        x[index + 1], x[index] = x[index], x[index + 1]
        self.dataChanged.emit(QModelIndex(), QModelIndex())


class ViewAssistMixin(object):
    selection_changed = Signal(QItemSelection, QItemSelection)
    # ... selected (set), deselected (set)
    selected_maydelete = Signal(bool, bool)
    # ... selected

    # -------------------------------------------------------------------------
    # Initialization and setting data (model)
    # -------------------------------------------------------------------------

    def __init__(self, session, modal_dialog_class, readonly=False):
        self.session = session
        self.modal_dialog_class = modal_dialog_class
        self.readonly = readonly
        self.selection_model = None

    def set_model_common(self, model, ListBase):
        if self.selection_model:
            self.selection_model.selectionChanged.disconnect()
        ListBase.setModel(self, model)
        self.selection_model = QItemSelectionModel(model)
        self.selection_model.selectionChanged.connect(self._selection_changed)
        self.setSelectionModel(self.selection_model)

    # -------------------------------------------------------------------------
    # Selection
    # -------------------------------------------------------------------------

    def clear_selection(self):
        # log.debug("GenericAttrTableView.clear_selection")
        if not self.selection_model:
            return
        self.selection_model.clearSelection()

    def get_selected_row_index(self):
        """Returns an integer or None."""
        selected_modelindex = self.get_selected_modelindex()
        if selected_modelindex is None:
            return None
        return selected_modelindex.row()

    def is_selected(self):
        row_index = self.get_selected_row_index()
        return row_index is not None

    def get_selected_object(self):
        index = self.get_selected_row_index()
        if index is None:
            return None
        model = self.model()
        if model is None:
            return None
        return model.get_object(index)

    def get_selected_modelindex(self):
        raise NotImplementedError()

    def go_to(self, row):
        model = self.model()
        if row is None:
            # Go to the end.
            nrows = model.rowCount()
            if nrows == 0:
                return
            row = nrows - 1
        modelindex = model.index(row, 0)  # second parameter is column
        self.setCurrentIndex(modelindex)

    def _selection_changed(self, selected, deselected):
        self.selection_changed.emit(selected, deselected)
        selected_model_indexes = selected.indexes()
        selected_row_indexes = [mi.row() for mi in selected_model_indexes]
        is_selected = bool(selected_row_indexes)
        model = self.model()
        may_delete = is_selected and all(
            [model.item_deletable(ri) for ri in selected_row_indexes])
        self.selected_maydelete.emit(is_selected, may_delete)

    def get_n_rows(self):
        model = self.model()
        return model.rowCount()

    # -------------------------------------------------------------------------
    # Add
    # -------------------------------------------------------------------------

    def insert_at_index(self, obj, index=None,
                        add_to_session=True, flush=True):
        # index: None for end, 0 for start
        model = self.model()
        model.insert_at_index(obj, index,
                              add_to_session=add_to_session, flush=flush)
        self.go_to(index)

    def insert_at_start(self, obj, add_to_session=True, flush=True):
        self.insert_at_index(obj, 0,
                             add_to_session=add_to_session, flush=flush)

    def insert_at_end(self, obj, add_to_session=True, flush=True):
        self.insert_at_index(obj, None,
                             add_to_session=add_to_session, flush=flush)

    def add_in_nested_transaction(self, new_object, at_index=None):
        # at_index: None for end, 0 for start
        if self.readonly:
            log.warning("Can't add; readonly")
            return
        try:
            with self.session.begin_nested():
                self.session.add(new_object)
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

    def remove_selected(self, delete_from_session=True):
        row_index = self.get_selected_row_index()
        self.remove_by_index(row_index,
                             delete_from_session=delete_from_session)

    def remove_by_index(self, row_index, delete_from_session=True):
        if row_index is None:
            return
        model = self.model()
        model.delete_item(row_index, delete_from_session=delete_from_session)

    # -------------------------------------------------------------------------
    # Move
    # -------------------------------------------------------------------------

    def move_selected_up(self):
        row_index = self.get_selected_row_index()
        if row_index is None or row_index == 0:
            return
        model = self.model()
        model.move_up(row_index)
        self.go_to(row_index - 1)

    def move_selected_down(self):
        row_index = self.get_selected_row_index()
        if row_index is None or row_index == self.get_n_rows() - 1:
            return
        model = self.model()
        model.move_down(row_index)
        self.go_to(row_index + 1)

    # -------------------------------------------------------------------------
    # Edit
    # -------------------------------------------------------------------------

    def edit(self, index, trigger, event):
        if trigger != QAbstractItemView.DoubleClicked:
            return False
        self.edit_by_modelindex(index)
        return False

    def edit_by_modelindex(self, index, readonly=None):
        if index is None:
            return
        if readonly is None:
            readonly = self.readonly
        model = self.model()
        item = model.listdata[index.row()]
        win = self.modal_dialog_class(self.session, item, readonly=readonly)
        win.edit_in_nested_transaction()

    def edit_selected(self, readonly=None):
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
    Takes a list and provides a view on it using str().
    Note that it MODIFIES THE LIST PASSED TO IT.
    """
    def __init__(self, data, session, parent=None):
        super().__init__(parent)  # QAbstractListModel
        DatabaseModelMixin.__init__(self, session=session)
        self.listdata = data

    def rowCount(self, parent=QModelIndex()):
        """Qt override."""
        return len(self.listdata)

    def data(self, index, role):
        """Qt override."""
        if index.isValid() and role == Qt.DisplayRole:
            return str(self.listdata[index.row()])
        return None


class ModalEditListView(QListView, ViewAssistMixin):

    # -------------------------------------------------------------------------
    # Initialization and setting data (model)
    # -------------------------------------------------------------------------

    def __init__(self, session, modal_dialog_class, *args, **kwargs):
        super().__init__(*args)  # QListView
        self.readonly = kwargs.pop('readonly', False)
        ViewAssistMixin.__init__(self, session=session,
                                 modal_dialog_class=modal_dialog_class,
                                 readonly=self.readonly)
        # self.setEditTriggers(QAbstractItemView.DoubleClicked)
        # ... probably only relevant if we do NOT override edit().
        # Being able to select a single row is the default.
        # Otherwise see SelectionBehavior and SelectionMode.

    def setModel(self, model):
        self.set_model_common(model, QListView)

    # -------------------------------------------------------------------------
    # Selection
    # -------------------------------------------------------------------------

    def get_selected_modelindex(self):
        """Returns a QModelIndex or None."""
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
    Takes a list of objects, a list of column headers;
    provides a view on it using str().
    Note that it MODIFIES THE LIST PASSED TO IT.

    Sorting: consider QSortFilterProxyModel
        ... but not clear that can do arbitrary column sorts, since its sorting
            is via its lessThan() function.

    The tricky part is keeping selections persistent after sorting.
    Not achieved yet. Simpler to wipe the selections.
    """
    # http://doc.qt.io/qt-4.8/qabstracttablemodel.html

    def __init__(self, data, header, session, default_sort_column_name=None,
                 default_sort_order=Qt.AscendingOrder,
                 deletable=True, parent=None):
        """
        header: list of colname, attr/func tuples
        """
        super().__init__(parent)  # QAbstractTableModel
        DatabaseModelMixin.__init__(self, session=session)
        self.listdata = data
        self.header_display = [x[0] for x in header]
        self.header_attr = [x[1] for x in header]
        self.session = session
        self.deletable = deletable
        self.default_sort_column_num = None
        self.default_sort_order = default_sort_order
        if default_sort_column_name is not None:
            self.default_sort_column_num = self.header_attr.index(
                default_sort_column_name)
            # ... will raise an exception if bad
            self.sort(self.default_sort_column_num, default_sort_order)

    def get_default_sort(self):
        return self.default_sort_column_num, self.default_sort_order

    def rowCount(self, parent=QModelIndex()):
        """Qt override."""
        return len(self.listdata)

    def columnCount(self, parent=QModelIndex()):
        """Qt override."""
        return len(self.header_attr)

    def data(self, index, role):
        """Qt override."""
        if index.isValid() and role == Qt.DisplayRole:
            obj = self.listdata[index.row()]
            colname = self.header_attr[index.column()]
            thing = getattr(obj, colname)
            if callable(thing):
                return str(thing())
            else:
                return str(thing)
        return None

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header_display[col]
        return None

    def sort(self, col, order):
        """Sort table by column number col."""
        # log.debug("GenericAttrTableModel.sort")
        if not self.listdata:
            return
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
        self.layoutChanged.emit()


class GenericAttrTableView(QTableView, ViewAssistMixin):
    selection_changed = Signal(QItemSelection, QItemSelection)

    # -------------------------------------------------------------------------
    # Initialization and setting data (model)
    # -------------------------------------------------------------------------

    def __init__(self, session, modal_dialog_class, parent=None, sortable=True,
                 stretch_last_section=True, readonly=False):
        super().__init__(parent=parent)  # QTableView
        ViewAssistMixin.__init__(self,
                                 session=session,
                                 modal_dialog_class=modal_dialog_class,
                                 readonly=readonly)
        self.sortable = sortable
        self.row_sizing_done = False
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSortingEnabled(sortable)
        hh = self.horizontalHeader()
        hh.setClickable(sortable)
        hh.sectionClicked.connect(self.clear_selection)
        # ... clear selection when we sort
        hh.setSortIndicatorShown(sortable)
        hh.setStretchLastSection(stretch_last_section)

    def setModel(self, model):
        self.set_model_common(model, QTableView)
        if self.sortable:
            colnum, order = model.get_default_sort()
            hh = self.horizontalHeader()
            hh.setSortIndicator(colnum, order)
        self.refresh_sizing()

    # -------------------------------------------------------------------------
    # Visuals
    # -------------------------------------------------------------------------

    def refresh_sizing(self):
        self.sizing_done = False
        self.resize()

    def resize(self):
        # Resize all rows to have the correct height
        if self.sizing_done:
            return
        self.resizeRowsToContents()
        self.resizeColumnsToContents()
        self.sizing_done = True

    # -------------------------------------------------------------------------
    # Selection
    # -------------------------------------------------------------------------

    def get_selected_modelindex(self):
        """Returns a QModelIndex or None."""
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
# Framework for radio buttons
# =============================================================================

class RadioGroup(object):
    def __init__(self, value_text_tuples, default=None):
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
            id = i + 1  # start with 1
            button = QRadioButton(text)
            self.bg.addButton(button, id)
            self.buttons.append(button)
            self.map_id_to_value[id] = value
            self.map_value_to_button[value] = button

    def get_value(self):
        buttongroup_id = self.bg.checkedId()
        if buttongroup_id == NOTHING_SELECTED:
            return None
        return self.map_id_to_value[buttongroup_id]

    def set_value(self, value):
        if value not in self.map_value_to_button:
            value = self.default_value
        button = self.map_value_to_button[value]
        button.setChecked(True)

    def add_buttons_to_layout(self, layout):
        for button in self.buttons:
            layout.addWidget(button)


# =============================================================================
# Decorator to stop whole program on exceptions (use for threaded slots)
# =============================================================================
# http://stackoverflow.com/questions/18740884
# http://stackoverflow.com/questions/308999/what-does-functools-wraps-do

def exit_on_exception(func):
    @wraps(func)
    def with_exit_on_exception(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            print("=" * 79)
            print("Uncaught exception in slot, within thread: {}".format(
                threading.current_thread().name))
            print("-" * 79)
            traceback.print_exc()
            print("-" * 79)
            print("args: {}".format(", ".join(repr(a) for a in args)))
            print("kwargs: {}".format(kwargs))
            print("=" * 79)
            sys.exit(1)
    return with_exit_on_exception


# =============================================================================
# Run a GUI, given a base window.
# =============================================================================

def run_gui(qt_app, win):
    win.show()
    return qt_app.exec_()
