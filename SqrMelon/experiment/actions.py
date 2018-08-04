from experiment.keyselection import selectNew, selectAdd, selectRemove, selectToggle
from experiment.curvemodel import HermiteKey
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


class RecursiveCommandError(Exception):
    pass


class NestedCommand(QUndoCommand):
    stack = []
    isUndo = False

    def __init__(self, label, parent=None):
        # if signal responses to undo() create additional commands we avoid creation
        if NestedCommand.isUndo:
            raise RecursiveCommandError()
        # if signal responses to redo() create additional commands we group them
        if NestedCommand.stack and parent is None:
            parent = NestedCommand.stack[-1]
        self.canPush = parent is None
        super(NestedCommand, self).__init__(label, parent)

    def _redoInternal(self):
        raise NotImplementedError()

    def _undoInternal(self):
        raise NotImplementedError()

    def redo(self):
        NestedCommand.stack.append(self)
        super(NestedCommand, self).redo()
        self._redoInternal()
        NestedCommand.stack.pop(-1)

    def undo(self):
        NestedCommand.isUndo = True
        self._undoInternal()
        super(NestedCommand, self).undo()
        NestedCommand.isUndo = False


class SelectionModelEdit(NestedCommand):
    """
    Very basic selection model edit,
    create & push on e.g. QItemSelectionModel.selectionChanged
    to make changes inherently undoable.

    NOTE: We assume that the selection change has already happened,
    so only after an undo() will redo() do anything.
    """

    def __init__(self, model, selected, deselected, emit, parent=None):
        # we can not create new undo commands during undo or redo
        super(SelectionModelEdit, self).__init__('Selection model change', parent)
        self.__model = model
        self.__emit = emit
        self.__selected = [unpackModelIndex(idx) for idx in selected.indexes()]
        self.__deselected = [unpackModelIndex(idx) for idx in deselected.indexes()]
        self.__isApplied = True  # the selection has already happened

    def _redoInternal(self):
        model = self.__model.model()

        added = QItemSelection()
        for index in self.__selected:
            mdlIndex = constructModelIndex(model, index)
            added.select(mdlIndex, mdlIndex)

        removed = QItemSelection()
        for index in self.__deselected:
            mdlIndex = constructModelIndex(model, index)
            removed.select(mdlIndex, mdlIndex)

        if not self.__isApplied:
            self.__model.select(added, QItemSelectionModel.Select)
            self.__model.select(removed, QItemSelectionModel.Deselect)

        self.__emit(added, removed)

    def _undoInternal(self):
        self.__isApplied = False

        model = self.__model.model()

        added = QItemSelection()
        for index in self.__selected:
            mdlIndex = constructModelIndex(model, index)
            added.select(mdlIndex, mdlIndex)

        removed = QItemSelection()
        for index in self.__deselected:
            mdlIndex = constructModelIndex(model, index)
            removed.select(mdlIndex, mdlIndex)

        self.__model.select(removed, QItemSelectionModel.Select)
        self.__model.select(added, QItemSelectionModel.Deselect)

        self.__emit(removed, added)


class KeySelectionEdit(NestedCommand):
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


class KeyEdit(QUndoCommand):
    """
    Assumes the keys are already changed and we are passing in the undo state.
    Caches current state during construction as redo state.

    first redo() will do nothing
    undo() will apply given state
    redo() will apply state chached during construction
    """

    def __init__(self, restore, triggerRepaint, parent=None):
        # type: (dict[HermiteKey, (float, float, float, float)], QUndoCommand) -> None
        super(KeyEdit, self).__init__('Key edit', parent)
        self.restore = restore
        self.triggerRepaint = triggerRepaint
        self.apply = {key: key.copyData() for key in restore}
        self.applied = True

    def redo(self):
        if self.applied:
            return
        self.applied = True
        for key, value in self.apply.iteritems():
            key._setData(*value)
        self.triggerRepaint()

    def undo(self):
        self.applied = False
        for key, value in self.restore.iteritems():
            key._setData(*value)
        self.triggerRepaint()


class MoveKeyAction(object):
    def __init__(self, selectedKeys, reproject, triggerRepaint):
        self.__reproject = reproject
        self.__initialState = {key: key.copyData() for key in selectedKeys}
        self.__dragStart = None
        self.__triggerRepaint = triggerRepaint
        self.__mask = 3

    def mousePressEvent(self, event):
        self.__dragStart = event.pos()
        if event.modifiers() == Qt.ShiftModifier:
            self.__mask = 0
        return False

    def mouseReleaseEvent(self, undoStack):
        undoStack.push(KeyEdit(self.__initialState, self.__triggerRepaint))
        return False

    def mouseMoveEvent(self, event):
        delta = event.pos() - self.__dragStart
        dx, dy = self.__reproject(delta.x(), delta.y())

        if not self.__mask:
            if abs(dx) > 4 and abs(dx) > abs(dy):
                self.__mask = 1
            if abs(dy) > 4 and abs(dy) > abs(dx):
                self.__mask = 2
            return

        for key, value in self.__initialState.iteritems():
            if self.__mask & 1:
                key._setX(value[0] + dx)
            if self.__mask & 2:
                key._setY(value[1] + dy)

        return True  # repaint

    def draw(self, painter):
        pass


class MoveTangentAction(object):
    def __init__(self, selectedTangents, reproject, triggerRepaint):
        self.__reproject = reproject
        self.__initialState = {(key, mask): key.copyData() for (key, mask) in selectedTangents}
        self.__dragStart = None
        self.__triggerRepaint = triggerRepaint

    def mousePressEvent(self, event):
        self.__dragStart = event.pos()
        return False

    def mouseReleaseEvent(self, undoStack):
        undoStack.push(KeyEdit(self.__initialState, self.__triggerRepaint))
        return False

    def mouseMoveEvent(self, event):
        delta = event.pos() - self.__dragStart
        dx, dy = self.__reproject(*delta)

        for entry, value in self.__initialState.iteritems():
            key, mask = entry
            if mask & 1:
                key._setInTangentY(value[2] + dy)
            if mask & 2:
                key._setOutTangentY(value[3] + dy)

        return True  # repaint

    def draw(self, painter):
        pass


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
