from experiment.keyselection import selectNew, selectAdd, selectRemove, selectToggle
from qtutil import *


def unpackModelIndex(qIndex):
    x = qIndex.column()
    y = qIndex.row()
    p = qIndex.parent()
    if p.isValid():
        return x, y, unpackModelIndex(p)
    return x, y, None


def constructModelIndex(model, unpacked):
    if unpacked[2] is not None:
        parent = constructModelIndex(model, unpacked[2])
    else:
        parent = QModelIndex()
    return model.index(unpacked[1], unpacked[0], parent)


class RecursionError(Exception): pass


class SelectionModelEdit(QUndoCommand):
    """
    Very basic selection model edit,
    create & push on e.g. QItemSelectionModel.selectionChanged
    to make changes inherently undoable.

    NOTE: We assume that the selection change has already happened,
    so only after an undo() will redo() do anything.
    """
    active = False

    def __init__(self, model, selected, deselected, parent=None):
        # we can not create new undo commands during undo or redo
        super(SelectionModelEdit, self).__init__('Selection model change', parent)
        self.__model = model
        self.__selected = [unpackModelIndex(idx) for idx in selected.indexes()]
        self.__deselected = [unpackModelIndex(idx) for idx in deselected.indexes()]
        self.__isApplied = True  # the selection has already happened

    def redo(self):
        if self.__isApplied:
            return

        SelectionModelEdit.active = True

        model = self.__model.model()
        for index in self.__selected:
            self.__model.select(constructModelIndex(model, index), QItemSelectionModel.Select)
        for index in self.__deselected:
            self.__model.select(constructModelIndex(model, index), QItemSelectionModel.Deselect)

        SelectionModelEdit.active = False

    def undo(self):
        SelectionModelEdit.active = True

        self.__isApplied = False
        model = self.__model.model()
        for index in self.__deselected:
            self.__model.select(constructModelIndex(model, index), QItemSelectionModel.Select)
        for index in self.__selected:
            self.__model.select(constructModelIndex(model, index), QItemSelectionModel.Deselect)

        SelectionModelEdit.active = False


class KeySelectionEdit(QUndoCommand):
    def __init__(self, selectionDict, keyStateDict, parent=None):
        super(KeySelectionEdit, self).__init__('Key selection change', parent)
        self.__selectionModel = selectionDict
        self.__apply = (keyStateDict.copy(), [])

        # move addOrModify actions to remove if we are modifying to '0'
        for key, value in self.__apply[0].iteritems():
            if value == 0:
                # all elements deselected, register for removal
                assert key in self.__selectionModel, 'Attempting to deselect key that wasn\'t selected.'
                self.__apply[1].append(key)

        for key in self.__apply[1]:
            del self.__apply[0][key]

        # cache restore state
        self.__restore = ({}, [])
        for addOrModify in self.__apply[0]:
            if addOrModify in self.__selectionModel:
                # is modification
                self.__restore[0][addOrModify] = self.__selectionModel[addOrModify]
            else:
                self.__restore[1].append(addOrModify)

        for remove in self.__apply[1]:
            self.__restore[0][remove] = self.__selectionModel[remove]

    def redo(self):
        oldState = self.__selectionModel.blockSignals(True)

        self.__selectionModel.update(self.__apply[0])
        for remove in self.__apply[1]:
            del self.__selectionModel[remove]

        self.__selectionModel.blockSignals(oldState)
        if not oldState:
            self.__selectionModel.changed.emit()

    def undo(self):
        oldState = self.__selectionModel.blockSignals(True)

        self.__selectionModel.update(self.__restore[0])
        for remove in self.__restore[1]:
            del self.__selectionModel[remove]

        self.__selectionModel.blockSignals(oldState)
        if not oldState:
            self.__selectionModel.changed.emit()


class MarqueeAction(object):
    def __init__(self, view, selectionDict):
        self.__view = view
        self.__selection = selectionDict
        self.__delta = {}

    def mousePressEvent(self, event):
        self.__start = event.pos()
        self.__end = event.pos()
        self.__mode = event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier)

    def _rect(self):
        x0, x1 = self.__start.x(), self.__end.x()
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = self.__start.y(), self.__end.y()
        y0, y1 = min(y0, y1), max(y0, y1)
        return x0, y0, x1 - x0, y1 - y0

    def mouseReleaseEvent(self, undoStack):
        # build apply state
        x, y, w, h = self._rect()
        itemsIter = self.__view.itemsAt(x, y, w, h)
        if self.__mode == Qt.NoModifier:
            selectNew(self.__selection, self.__delta, itemsIter)
        elif self.__mode == Qt.ControlModifier | Qt.ShiftModifier:
            selectAdd(self.__selection, self.__delta, itemsIter)
        elif self.__mode == Qt.ControlModifier:
            selectRemove(self.__selection, self.__delta, itemsIter)
        else:  # if self.mode == Qt.ShiftModifier:
            selectToggle(self.__selection, self.__delta, itemsIter)

        # if we don't plan to change anything, stop right here and don't submit this undoable action
        if not self.__delta:
            return True

        # commit self to undo stack
        undoStack.push(KeySelectionEdit(self.__selection, self.__delta))

    def mouseMoveEvent(self, event):
        self.__end = event.pos()
        return True

    def draw(self, painter):
        x, y, w, h = self._rect()
        painter.setPen(QColor(0, 160, 255, 255))
        painter.setBrush(QColor(0, 160, 255, 64))
        painter.drawRect(x, y, w, h)
