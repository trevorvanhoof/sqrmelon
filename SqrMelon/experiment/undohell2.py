from collections import OrderedDict
from qtutil import *
from util import randomColor


class HermiteKey(object):
    __slots__ = ('x', 'y', 'inTangentY', 'outTangentY')

    def __init__(self, x=0.0, y=0.0, inTangentY=0.0, outTangentY=0.0):
        # type: (float, float, float, float) -> None
        self.x = x
        self.y = y
        self.inTangentY = inTangentY
        self.outTangentY = outTangentY


def binarySearch(value, data, key=lambda x: x):
    # finds value in data, assumes data is sorted small to large
    a, b = 0, len(data) - 1
    index = -1
    while a <= b:
        index = (a + b) / 2
        valueAtIndex = key(data[index])
        if valueAtIndex < value:
            # target is in right half
            a = index + 1
            index += 1  # in case we're done we need to insert right
        elif valueAtIndex > value:
            # target is in left half
            b = index - 1
        else:
            return index
    return index


class KeySelection(QObject):
    changed = pyqtSignal()

    # dict of HermiteKey objects and bitmask of (point, intangent, outtangent)

    def __init__(self):
        super(KeySelection, self).__init__()
        self.__data = {}

    def __repr__(self):
        return str(self.__data)

    def __iter__(self):
        for key in self.__data:
            yield key

    def copy(self):
        return self.__data.copy()

    def clear(self):
        self.__data.clear()

    def get(self, item, fallback):
        return self.__data.get(item, fallback)

    def setdefault(self, item, fallback):
        return self.__data.setdefault(item, fallback)

    def iteritems(self):
        return self.__data.iteritems()

    def iterkeys(self):
        return self.__data.iterkeys()

    def itervalues(self):
        return self.__data.itervalues()

    def __contains__(self, item):
        return item in self.__data

    def __getitem__(self, item):
        return self.__data[item]

    def __setitem__(self, item, value):
        self.__data[item] = value
        self.changed.emit()

    def update(self, other):
        self.__data.update(other)
        self.changed.emit()

    def __delitem__(self, item):
        del self.__data[item]
        self.changed.emit()


# TODO: Mimic maya? when mask is tangent, always deselect key; when selecting, first attempt to select keys, if no keys found then attempt to select tangents
def _select(change, key, existing, mask):
    change[key] = change.setdefault(key, existing) | mask


def _deselect(change, key, existing, mask):
    change[key] = change.setdefault(key, existing) & (~mask)


def selectNew(selection, change, itemsIter):
    # creating new selection, first change is to remove everything
    for key in selection:
        change[key] = 0
    for key, mask in itemsIter:
        # overwrite removed elements with only selected elements
        _select(change, key, selection.get(key, 0), mask)


def selectAdd(selection, change, itemsIter):
    for key, mask in itemsIter:
        # make sure value is new to selection & register for selection
        if key not in selection or not (selection[key] & mask):
            _select(change, key, selection.get(key, 0), mask)


def selectRemove(selection, change, itemsIter):
    for key, mask in itemsIter:
        # make sure value exists in selection & mask out the element to remove
        if key in selection and selection[key] & mask:
            _deselect(change, key, selection[key], mask)


def selectToggle(selection, change, itemsIter):
    for key, mask in itemsIter:
        # make sure value is new to selection & register for selection
        if key not in selection or not (selection[key] & mask):
            _select(change, key, selection.get(key, 0), mask)
        # make sure value exists in selection & mask out the element to remove
        if key in selection and selection[key] & mask:
            _deselect(change, key, selection[key], mask)


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


class Enum(object):
    def __init__(self, label):
        assert label in self.options()
        self.__label = label

    def __str__(self):
        return self.__label

    def index(self):
        return self.options().index(self.__label)

    @staticmethod
    def options():
        raise NotImplementedError()


class ELoopMode(Enum):
    @staticmethod
    def options():
        return 'Clamp', 'Loop'


class ItemRow(object):
    """ Represent a row of QStandardItems """

    def __init__(self, name, *args):
        items = [QStandardItem(name)]
        items[0].setData(self)
        self.__dict__['items'] = items
        self.__dict__['color'] = QColor(*randomColor())

        for value in args:
            self.items.append(QStandardItem(str(value)))
            # implicitly cast simple types when getting their values
            # allows direct UI editing as well
            if isinstance(value, (float, int, bool, basestring, Enum)):
                value = type(value)
            # else:
            #    items[-1].setEditable(False)
            items[-1].setData(value)

    @property
    def name(self):
        return self.items[0].text()

    def __getitem__(self, index):
        item = self.items[index]
        if index == 0:
            return item.text()

        data = item.data()

        if isinstance(data, type):
            return data(item.text())

        return data

    def __setitem__(self, index, value):
        item = self.items[index]
        if index == 0:
            item.setText(value)
            return

        item.setText(str(value))

        data = item.data()
        if isinstance(data, type):
            return

        item.setData(value)

    def __str__(self):
        return self.items[0].text()

    @classmethod
    def properties(cls):
        raise NotImplementedError()

    def __getattr__(self, attr):
        try:
            i = self.__class__.properties().index(attr)
        except ValueError:
            raise AttributeError(attr)
        return self[i]

    def __setattr__(self, attr, value):
        try:
            i = self.__class__.properties().index(attr)
        except ValueError:
            raise AttributeError(attr)
        self[i] = value


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
            if self.__typ == float:
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
        names = self.columnNames()
        mdl.setHorizontalHeaderLabels(names)
        self.verticalHeader().hide()
        self.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        self.horizontalHeader().setResizeMode(0, QHeaderView.Interactive)
        for i in xrange(1, len(names) - 1):
            self.horizontalHeader().setResizeMode(i, QHeaderView.ResizeToContents)
        self.horizontalHeader().setResizeMode(len(names) - 1, QHeaderView.Stretch)
        self.setItemDelegate(AtomDelegate())

    @staticmethod
    def columnNames():
        raise NotImplementedError()


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


class Clip(ItemRow):
    def __init__(self, name, loopMode):
        super(Clip, self).__init__(name, loopMode)
        self.__dict__['curves'] = QStandardItemModel()
        self.__dict__['textures'] = OrderedDict()

    @classmethod
    def properties(cls):
        return 'name', 'loopMode'


class HermiteCurve(ItemRow):
    def __init__(self, name, data=None):
        super(HermiteCurve, self).__init__(name)
        self.__dict__['keys'] = data or []

    @classmethod
    def properties(cls):
        return 'name',

    def evaluate(self, x):
        index = binarySearch(x, self.keys, lambda key: key.x)

        # x before first key, possibly faster to test x explicitly before binary search
        if index == 0:
            return self.keys[0].y

        # x after last key, possibly faster to test x explicitly before binary search
        if index >= len(self.keys):
            return self.keys[-1].y

        prev = self.keys[index - 1]
        next = self.keys[index]

        t = (x - prev.x) / float(next.x - prev.x)

        tt = t * t
        ttt = t * tt

        tt2 = tt + tt
        tt3 = tt2 + tt
        ttt2 = ttt + ttt

        h00t = ttt2 - tt3 + 1.0
        h10t = ttt - tt2 + t
        h01t = tt3 - ttt2
        h11t = ttt - tt

        return (h00t * prev.y +
                h10t * prev.outTangentY +
                h11t * next.inTangentY +
                h01t * next.y)


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
                undoStack.push(cmd)
            else:
                cmd.redo()
        except RecursiveCommandError:
            pass

    @staticmethod
    def columnNames():
        return Clip.properties()


class Curve(ItemRow):
    def __init__(self, name):
        super(Curve, self).__init__(name)

    @classmethod
    def properties(cls):
        return 'name',


class CurveList(UndoableSelectionView):
    def __init__(self, source, undoStack, parent=None):
        super(CurveList, self).__init__(undoStack, parent)
        self._source = source
        source.selectionChange.connect(self._pull)

    def _pull(self, *args):
        # get first selected container
        curves = None  # empty stub
        for container in self._source.selectionModel().selectedRows():
            curves = container.data(Qt.UserRole + 1).curves
            break
        if self.model() == curves:
            return
        if curves is None:
            self.clearSelection()
        self.setModel(curves)
        self.selectAll()


class CurveView(QWidget):
    def __init__(self, source, undoStack, parent=None):
        super(CurveView, self).__init__(parent)
        self._source = source
        source.selectionChange.connect(self._pull)

        self._visibleCurves = set()
        self.setFocusPolicy(Qt.StrongFocus)
        self._selectionModel = KeySelection()
        self._selectionModel.changed.connect(self.repaint)
        self._undoStack = undoStack
        self.action = None

        # camera
        self.left = -1.0
        self.right = 13.0
        self.top = 2.0
        self.bottom = -1.0

    def _pull(self, *args):
        newState = {index.data(Qt.UserRole + 1) for index in self._source.selectionModel().selectedRows()}
        deselected = self._visibleCurves - newState
        self._visibleCurves = newState

        # when curves are deselected, we must deselect their keys as well
        keyStateChange = {}
        for curve in deselected:
            for key in curve.keys:
                if key in self._selectionModel:
                    keyStateChange[key] = 0

        # no keys to deselect
        if not keyStateChange:
            self.repaint()
            return

        try:
            cmd = KeySelectionEdit(self._selectionModel, keyStateChange)
            if cmd.canPush:
                self._undoStack.push(cmd)
            else:
                cmd.redo()
        except RecursiveCommandError:
            pass

    # mapping functions
    def xToT(self, x):
        return (x / float(self.width())) * (self.right - self.left) + self.left

    def tToX(self, t):
        return ((t - self.left) / (self.right - self.left)) * self.width()

    def yToV(self, y):
        return (y / float(self.height())) * (self.bottom - self.top) + self.top

    def vToY(self, v):
        return ((v - self.top) / (self.bottom - self.top)) * self.height()

    def uToPx(self, t, v):
        return self.tToX(t), self.vToY(v)

    def pxToU(self, x, y):
        return self.xToT(x), self.yToV(y)

    def _tangentEndPoint(self, src, dst, wt):
        TANGENT_LENGTH = 20.0
        x0, y0 = self.uToPx(src.x, src.y)
        x1, y1 = self.uToPx(dst.x, dst.y)
        dx = x1 - x0
        dy = abs(y1 - y0) * wt
        f = TANGENT_LENGTH / ((dx * dx + dy * dy) ** 0.5)
        x1, y1 = x0 + dx * f, y0 + dy * f
        return x1, y1

    def _drawTangent(self, painter, isSelected, src, dst, wt):
        # selection
        if isSelected:
            painter.setPen(Qt.white)
        else:
            painter.setPen(Qt.magenta)

        x0, y0 = self.uToPx(src.x, src.y)
        x1, y1 = self._tangentEndPoint(src, dst, wt)
        painter.drawLine(x0, y0, x1, y1)
        painter.drawRect(x1 - 1, y1 - 1, 2, 2)

    def itemsAt(self, x, y, w, h):
        for curve in self._visibleCurves:
            for i, key in enumerate(curve.keys):
                kx, ky = self.uToPx(key.x, key.y)
                if x <= kx <= x + w and y < ky <= y + h:
                    yield key, 1

                if key not in self._selectionModel:
                    # key or tangent must be selected for tangents to be visible
                    continue

                # in tangent
                if i > 0:
                    kx, ky = self._tangentEndPoint(key, curve.keys[i - 1], key.inTangentY)
                    if x <= kx <= x + w and y < ky <= y + h:
                        yield key, 1 << 1

                # out tangent
                if i < len(curve.keys) - 1:
                    kx, ky = self._tangentEndPoint(key, curve.keys[i + 1], -key.outTangentY)
                    if x <= kx <= x + w and y < ky <= y + h:
                        yield key, 1 << 2

    def paintEvent(self, event):
        painter = QPainter(self)
        ppt = None

        painter.fillRect(QRect(0, 0, self.width(), self.height()), QColor(40, 40, 40, 255))

        # paint evaluated data
        for curve in self._visibleCurves:
            for x in xrange(0, self.width(), 4):
                t = self.xToT(x)
                y = self.vToY(curve.evaluate(t))
                pt = QPoint(x, y)
                if x:
                    painter.drawLine(ppt, pt)
                ppt = pt

        # paint key points
        for curve in self._visibleCurves:
            for i, key in enumerate(curve.keys):
                # if key is selected, paint tangents
                selectionState = self._selectionModel.get(key, 0)

                # key selected
                if selectionState & 1:
                    painter.setPen(Qt.yellow)
                else:
                    painter.setPen(Qt.black)

                # key
                x, y = self.uToPx(key.x, key.y)
                painter.drawRect(x - 2, y - 2, 4, 4)

                # tangents not visible
                if not selectionState:
                    continue

                # in tangent
                if i > 0:
                    self._drawTangent(painter, selectionState & (1 << 1), key, curve.keys[i - 1], key.inTangentY)

                # out tangent
                if i < len(curve.keys) - 1:
                    self._drawTangent(painter, selectionState & (1 << 2), key, curve.keys[i + 1], -key.outTangentY)

        if self.action is not None:
            self.action.draw(painter)

    def mousePressEvent(self, event):
        self.action = MarqueeAction(self, self._selectionModel)
        if self.action.mousePressEvent(event):
            self.repaint()

    def mouseReleaseEvent(self, event):
        action = self.action
        self.action = None
        # make sure self.action is None before calling mouseReleaseEvent so that:
        # 1. when returning True we will clear any painting done by self.action during mousePress/-Move
        # 2. when a callback results in a repaint the above holds true
        if action and action.mouseReleaseEvent(self._undoStack):
            self.repaint()

    def mouseMoveEvent(self, event):
        if self.action:
            if self.action.mouseMoveEvent(event):
                self.repaint()


if __name__ == '__main__':
    a = QApplication([])

    undoStack = QUndoStack()
    undoView = QUndoView(undoStack)

    clip0 = Clip('Clip 0', ELoopMode('Clamp'))
    clip0.curves.appendRow(HermiteCurve('uOrigin.x', [HermiteKey(0.0, 0.0, 0.0, 0.0), HermiteKey(1.0, 1.0, 1.0, 1.0)]).items)
    clip0.curves.appendRow(HermiteCurve('uFlash', [HermiteKey(0.0, 1.0, 1.0, 1.0), HermiteKey(1.0, 0.0, 0.0, 0.0)]).items)

    clip1 = Clip('Clip 1', ELoopMode('Loop'))
    clip1.curves.appendRow(HermiteCurve('uOrigin.x', [HermiteKey(2.0, 0.0, 0.0, 0.0), HermiteKey(3.0, 1.0, 0.0, 0.0)]).items)
    clip1.curves.appendRow(HermiteCurve('uOrigin.y', [HermiteKey(0.0, 0.0, 1.0, 1.0), HermiteKey(1.0, 1.0, 1.0, 1.0)]).items)

    clipManager = UndoableSelectionView(undoStack)
    clipManager.model().appendRow(clip0.items)
    clipManager.model().appendRow(clip1.items)

    curveList = CurveList(clipManager, undoStack)

    curveView = CurveView(curveList, undoStack)

    mainContainer = QSplitter(Qt.Vertical)
    mainContainer.addWidget(undoView)
    mainContainer.addWidget(clipManager)
    mainContainer.addWidget(curveList)
    mainContainer.addWidget(curveView)

    mainWindow = QMainWindow()
    mainWindow.setCentralWidget(mainContainer)
    mainWindow.show()
    # makes sure qt cleans up & python stops after closing the main window; https://stackoverflow.com/questions/39304366/qobjectstarttimer-qtimer-can-only-be-used-with-threads-started-with-qthread
    mainWindow.setAttribute(Qt.WA_DeleteOnClose)

    a.exec_()
