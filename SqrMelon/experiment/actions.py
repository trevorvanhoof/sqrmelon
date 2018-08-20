from experiment.enums import ETangentMode
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


class EventEdit(QUndoCommand):
    """
    Assumes the events are already changed and we are passing in the undo state.
    Caches current state during construction as redo state.

    first redo() will do nothing
    undo() will apply given state
    redo() will apply state chached during construction
    """

    def __init__(self, restore, parent=None):
        super(EventEdit, self).__init__('Event edit', parent)
        self._apply = {event: (event.start, event.end, event.track) for event in restore.iterkeys()}
        self._restore = restore.copy()
        self.applied = True

    def redo(self):
        if self.applied:
            return
        self.applied = True
        for event, value in self._apply.iteritems():
            event.start, event.end, event.track = value

    def undo(self):
        self.applied = False
        for event, value in self._restore.iteritems():
            event.start, event.end, event.track = value


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
    def __init__(self, originalTime, xToT, setTime, undoable=True):
        self.__originalTime = originalTime
        self.__setTime = setTime
        self.__xToT = xToT
        self.__newTime = originalTime
        self.__undoable = undoable

    def mousePressEvent(self, event):
        pass

    def mouseMoveEvent(self, event):
        self.__newTime = self.__xToT(event.x())
        self.__setTime(self.__newTime)

    def mouseReleaseEvent(self, undoStack):
        if self.__undoable:
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


class MoveEventAction(DirectionalAction):
    def __init__(self, reproject, cellSize, events, handle=3):
        super(MoveEventAction, self).__init__(reproject)
        self._events = {event: (event.start, event.end, event.track) for event in events}
        self._cellSize = cellSize / 8.0  # Snap at 1/8th of a grid cell
        self._handle = handle
        self._cursorOverride = False

    def mousePressEvent(self, event):
        if self._handle in (1, 2):
            # Change cursor to horizontal move when dragging start or end section
            QApplication.setOverrideCursor(Qt.SizeHorCursor)
            self._cursorOverride = True

        return super(MoveEventAction, self).mousePressEvent(event)

    def mouseReleaseEvent(self, undoStack):
        undoStack.push(EventEdit(self._events))
        if self._cursorOverride:
            QApplication.restoreOverrideCursor()

    def processMouseDelta(self, event):
        from experiment.timelineview import GraphicsItemEvent
        ux, uy = self._reproject(event.x(), event.y())
        ux -= self._dragStartU[0]
        uy = (event.y() - self._dragStartPx.y()) / float(GraphicsItemEvent.trackHeight)

        for event, value in self._events.iteritems():
            if self._mask & 1:  # X move
                newStart = round(value[0] + ux, 3)
                newEnd = round(value[1] + ux, 3)

                # Snap
                newStart = round(newStart / self._cellSize) * self._cellSize
                newEnd = round(newEnd / self._cellSize) * self._cellSize

                if self._handle & 1 and newStart != event.start:
                    if not self._handle & 2:
                        # truncate from start
                        event.duration = event.end - newStart
                    event.start = newStart

                if self._handle == 2:
                    # truncate from end
                    if newEnd != event.end:
                        event.end = newEnd

            if self._mask & 2:  # Y move
                newTrack = int(round(value[2] + uy))
                if newTrack != event.track:
                    event.track = newTrack

    def draw(self, painter):
        pass


class MarqueeActionBase(object):
    CLICK_SIZE = 10

    def __init__(self, view, selection):
        self._view = view
        self._selection = selection
        self._delta = None

    def mousePressEvent(self, event):
        self._start = event.pos()
        self._end = event.pos()
        self._mode = event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier)

    def _rect(self):
        x0, x1 = self._start.x(), self._end.x()
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = self._start.y(), self._end.y()
        y0, y1 = min(y0, y1), max(y0, y1)
        return x0, y0, x1 - x0, y1 - y0

    @staticmethod
    def _selectNew(selection, itemsIter):
        raise NotImplementedError()

    @staticmethod
    def _selectAdd(selection, itemsIter):
        raise NotImplementedError()

    @staticmethod
    def _selectRemove(selection, itemsIter):
        raise NotImplementedError()

    @staticmethod
    def _selectToggle(selection, itemsIter):
        raise NotImplementedError()

    @staticmethod
    def _createCommand(selection, delta):
        raise NotImplementedError()

    def mouseReleaseEvent(self, undoStack):
        if self._end == self._start:
            x, y, w, h = self._start.x() - (self.CLICK_SIZE / 2), \
                         self._start.y() - (self.CLICK_SIZE / 2), \
                         self.CLICK_SIZE, \
                         self.CLICK_SIZE
        else:
            x, y, w, h = self._rect()
        # build apply state
        itemsIter = self._view.itemsAt(x, y, w, h)
        if self._mode == Qt.NoModifier:
            self._delta = self._selectNew(self._selection, itemsIter)
        elif self._mode == Qt.ControlModifier | Qt.ShiftModifier:
            self._delta = self._selectAdd(self._selection, itemsIter)
        elif self._mode == Qt.ControlModifier:
            self._delta = self._selectRemove(self._selection, itemsIter)
        else:  # if self.mode == Qt.ShiftModifier:
            self._delta = self._selectToggle(self._selection, itemsIter)

        # if we don't plan to change anything, stop right here and don't submit this undoable action
        if not self._delta:
            return True

        # commit self to undo stack
        cmd = self._createCommand(self._selection, self._delta)
        if cmd:
            undoStack.push(cmd)

    def mouseMoveEvent(self, event):
        self._end = event.pos()
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
