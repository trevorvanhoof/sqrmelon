from experiment.enums import ETangentMode
from experiment.keyselection import selectNew, selectAdd, selectRemove, selectToggle
from experiment.curvemodel import HermiteKey, EInsertMode
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
        # type: (dict[HermiteKey, (float, float, float, float)], (), QUndoCommand) -> None
        super(KeyEdit, self).__init__('Key edit', parent)
        self.restore = restore
        self.triggerRepaint = triggerRepaint
        self.apply = {key: key.copyData() for key in restore}
        self.curves = {key.parent for key in restore}
        self.applied = True

    def redo(self):
        if self.applied:
            return
        self.applied = True
        for key, value in self.apply.iteritems():
            key.setData(*value)
        for curve in self.curves:
            curve.sort()
        self.triggerRepaint()

    def undo(self):
        self.applied = False
        for key, value in self.restore.iteritems():
            key.setData(*value)
        for curve in self.curves:
            curve.sort()
        self.triggerRepaint()


class CurveModelEdit(QUndoCommand):
    def __init__(self, model, pyObjsToAppend, rowIndicesToRemove, parent=None):
        super(CurveModelEdit, self).__init__('Create / delete curves', parent)
        self.model = model
        self.pyObjsToAppend = pyObjsToAppend
        self.rowIndicesToRemove = sorted(rowIndicesToRemove)
        self.removedRows = []
        self.modelSizeAfterRemoval = None

    def redo(self):
        # remove rows at inidices, starting at the highest index
        self.removedRows = []
        for row in reversed(self.rowIndicesToRemove):
            self.removedRows.append(self.model.takeRow(row))

        # append additional rows
        self.modelSizeAfterRemoval = self.model.rowCount()
        for row in self.pyObjsToAppend:
            self.model.appendRow(row.items)

    def undo(self):
        # remove appended items, before reinserting
        while self.model.rowCount() > self.modelSizeAfterRemoval:
            self.model.takeRow(self.model.rowCount() - 1)

        # reinsert removed rows
        for row in self.rowIndicesToRemove:
            self.model.insertRow(row, self.removedRows.pop(0))


class TimeEdit(QUndoCommand):
    def __init__(self, originalTime, newTime, setTime, parent=None):
        super(TimeEdit, self).__init__('Time changed', parent)
        self.originalTime = originalTime
        self.newTime = newTime
        self.setTime = setTime
        self.applied = True

    def redo(self):
        if self.applied:
            return
        self.applied = True
        self.setTime(self.newTime)

    def undo(self):
        self.applied = False
        self.setTime(self.originalTime)


class MoveTimeAction(object):
    def __init__(self, originalTime, xToT, setTime):
        self.__originalTime = originalTime
        self.__setTime = setTime
        self.__xToT = xToT
        self.__newTime = originalTime

    def mousePressEvent(self, event):
        pass

    def mouseMoveEvent(self, event):
        self.__newTime = self.__xToT(event.x())
        self.__setTime(self.__newTime)

    def mouseReleaseEvent(self, undoStack):
        undoStack.push(TimeEdit(self.__originalTime, self.__newTime, self.__setTime))

    def draw(self, painter):
        pass


class DirectionalAction(object):
    def __init__(self, reproject, mask=3):
        self._reproject = reproject
        self._dragStartPx = None
        self._dragStartU = None
        self._mask = mask

    def mousePressEvent(self, event):
        self._dragStartPx = event.pos()
        self._dragStartU = self._reproject(event.x(), event.y())
        # when we are omni-directional and shift is pressed we can lock the event to a single axis
        if self._mask == 3 and event.modifiers() == Qt.ShiftModifier:
            self._mask = 0
        return False

    def mouseMoveEvent(self, event):
        if not self._mask:
            deltaPx = event.pos() - self._dragStartPx
            dxPx = deltaPx.x()
            dyPx = deltaPx.y()
            if abs(dxPx) > 4 and abs(dxPx) > abs(dyPx):
                self._mask = 1
            if abs(dyPx) > 4 and abs(dyPx) > abs(dxPx):
                self._mask = 2
            return

        return self.processMouseDelta(event)

    def processMouseDelta(self, event):
        raise NotImplementedError()

    def draw(self, painter):
        pass


class MoveKeyAction(DirectionalAction):
    def __init__(self, reproject, selectedKeys, triggerRepaint):
        super(MoveKeyAction, self).__init__(reproject)
        self.__curves = {key.parent for key in selectedKeys}
        self.__selectedKeys = list(selectedKeys.iterkeys())
        self.__initialState = {key: key.copyData() for curve in self.__curves for key in curve.keys}
        self.__triggerRepaint = triggerRepaint

    def mouseReleaseEvent(self, undoStack):
        undoStack.push(KeyEdit(self.__initialState, self.__triggerRepaint))
        return False

    def processMouseDelta(self, event):
        ux, uy = self._reproject(event.x(), event.y())
        ux -= self._dragStartU[0]
        uy -= self._dragStartU[1]

        for key in self.__selectedKeys:
            value = self.__initialState[key]
            if self._mask & 1:
                key.x = value[0] + ux
            if self._mask & 2:
                key.y = value[1] + uy

        if self._mask & 1:
            for curve in self.__curves:
                curve.sort()

        # must do this after sorting...
        for key in self.__initialState:
            key.computeTangents()

        return True  # repaint


class MoveTangentAction(object):
    def __init__(self, selectedTangents, reproject, triggerRepaint):
        self.__reproject = reproject
        self.__initialState = {key: key.copyData() for (key, mask) in selectedTangents.iteritems()}
        self.__masks = selectedTangents.copy()
        self.__dragStart = None
        self.__triggerRepaint = triggerRepaint

    def mousePressEvent(self, event):
        self.__dragStart = self.__reproject(event.x(), event.y())
        return False

    def mouseReleaseEvent(self, undoStack):
        undoStack.push(KeyEdit(self.__initialState, self.__triggerRepaint))
        return False

    def mouseMoveEvent(self, event):
        dx, dy = self.__reproject(event.x(), event.y())
        dx -= self.__dragStart[0]
        dy -= self.__dragStart[1]

        for key, value in self.__initialState.iteritems():
            mask = self.__masks[key]
            if mask & 2:
                key.inTangentY = value[2] - dy
                key.inTangentMode = ETangentMode.Custom
            if mask & 4:
                key.outTangentY = value[3] + dy
                key.outTangentMode = ETangentMode.Custom

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
        if self.__end == self.__start:
            x, y, w, h = self.__start.x() - 5, self.__start.y() - 5, 10, 10
        else:
            x, y, w, h = self._rect()
        # build apply state
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


class DeleteKeys(QUndoCommand):
    def __init__(self, apply, triggerRepaint, parent=None):
        super(DeleteKeys, self).__init__('Delete keys', parent)
        self.apply = apply
        self.triggerRepaint = triggerRepaint

    def redo(self):
        for curve, keys in self.apply.iteritems():
            curve.removeKeys(keys)
        self.triggerRepaint()

    def undo(self):
        for curve, keys in self.apply.iteritems():
            curve.insertKeys(keys)
        self.triggerRepaint()


class InsertKeys(QUndoCommand):
    def __init__(self, apply, triggerRepaint, parent=None):
        super(InsertKeys, self).__init__('Insert keys', parent)
        self.apply = apply
        self.triggerRepaint = triggerRepaint
        self.alteredKeys = {}

    def redo(self):
        for curve, key in self.apply.iteritems():
            other = curve.insertKey(key, EInsertMode.Passive)
            if other is not None:
                self.alteredKeys[curve] = other
        self.triggerRepaint()

    def undo(self):
        for curve, key in self.apply.iteritems():
            if curve in self.alteredKeys:
                self.alteredKeys[curve][0].setData(*self.alteredKeys[curve][1])
            else:
                curve.removeKeys([key])
        self.triggerRepaint()
