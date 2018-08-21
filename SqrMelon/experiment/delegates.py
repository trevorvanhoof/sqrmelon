from experiment.actions import SelectionModelEdit, RecursiveCommandError
from experiment.enum import Enum
from qtutil import *


class LineEdit(QLineEdit):
    def value(self):
        return self.text()

    def setValue(self, text):
        self.setText(text)


class EnumEdit(QComboBox):
    def __init__(self, enum, parent=None):
        super(EnumEdit, self).__init__(parent)
        self.__enum = enum
        self.addItems(enum.options())
        self.editingFinished = self.currentIndexChanged

    def focusInEvent(self, evt):
        # we get multiple focus in events while spawning the item delegate
        # the last one is a popupFocusReason, but this popup is immediately cancelled again
        # so we delay the popup to skip over the lose-focus event while trying to gain focus
        if evt.reason() == 7:
            self.__t = QTimer()
            self.__t.timeout.connect(self.showPopup)
            self.__t.setSingleShot(True)
            self.__t.start(100)

    def value(self):
        return self.currentText()

    def setValue(self, text):
        # cast back and forth to ensure label is valid
        if isinstance(text, Enum):
            text = str(text)
        try:
            value = self.__enum(text)
        except AssertionError:
            # invalid text, don't change
            return
        self.setCurrentIndex(value.index())


class AtomDelegate(QItemDelegate):
    def setEditorData(self, editorWidget, index):
        editorWidget.setValue(self.__typ(index.data(Qt.EditRole)))

    def setModelData(self, editorWidget, model, index):
        model.setData(index, str(editorWidget.value()))

    def createEditor(self, parentWidget, styleOption, index):
        if index.column() == 0:
            # special case for self-referencing item
            self.__typ = str
            self.__editor = LineEdit()
        else:
            self.__typ = index.data(Qt.UserRole + 1)
            if not isinstance(self.__typ, type):
                return
            if self.__typ == int:
                self.__editor = SpinBox()
                self.__editor.setMinimum(-2**31)
                self.__editor.setMaximum(2**31-1)
            elif self.__typ == float:
                self.__editor = DoubleSpinBox()
            elif self.__typ == basestring or issubclass(self.__typ, basestring):
                self.__editor = LineEdit()
            elif issubclass(self.__typ, Enum):
                self.__editor = EnumEdit(self.__typ)
            else:
                return
        self.__editor.setParent(parentWidget)
        self.__editor.editingFinished.connect(self.__commitAndCloseEditor)
        return self.__editor

    def __commitAndCloseEditor(self):
        self.commitData.emit(self.__editor)
        self.closeEditor.emit(self.__editor, QAbstractItemDelegate.NoHint)


class NamedColums(QTableView):
    def __init__(self, parent=None):
        super(NamedColums, self).__init__(parent)
        self.setSelectionMode(QTableView.ExtendedSelection)
        self.setSelectionBehavior(QTableView.SelectRows)
        mdl = QStandardItemModel()
        self.setModel(mdl)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(22)
        self._updateNames()
        self.setItemDelegate(AtomDelegate())
        self.setStyleSheet('QTableView { selection-background-color: rgb(188,220,244); }'
                           'QTableView:active { selection-background-color: rgb(0,120,215); }')

    def _updateNames(self):
        names = self.columnNames()
        if self.model():
            self.model().setHorizontalHeaderLabels(names)
            self.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
            self.horizontalHeader().setResizeMode(0, QHeaderView.Interactive)
            for i in xrange(1, len(names) - 1):
                self.horizontalHeader().setResizeMode(i, QHeaderView.ResizeToContents)
            self.horizontalHeader().setResizeMode(len(names) - 1, QHeaderView.Stretch)

    @staticmethod
    def columnNames():
        raise NotImplementedError()


class UndoableSelectionView(NamedColums):
    selectionChange = pyqtSignal(QItemSelection, QItemSelection)

    def __init__(self, undoStack, parent=None):
        super(UndoableSelectionView, self).__init__(parent)
        self._undoStack = undoStack

    def setModel(self, model):
        if model is None:
            # deselect all
            self.selectionChange.emit(QItemSelection(), self.selectionModel().selection())

        super(UndoableSelectionView, self).setModel(model)
        self.selectionModel().selectionChanged.connect(self.__selectionChanged)

    def __selectionChanged(self, selected, deselected):
        try:
            cmd = SelectionModelEdit(self.selectionModel(), selected, deselected, self.selectionChange.emit)
            if cmd.canPush:
                self._undoStack.push(cmd)
            else:
                cmd.redo()
        except RecursiveCommandError:
            pass
