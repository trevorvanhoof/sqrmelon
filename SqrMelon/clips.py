from qtutil import *
from collections import OrderedDict
from util import randomColor


class HermiteKey(object):
    __slots__ = ('x', 'y', 'inTangentY', 'outTangentY')

    def __init__(self, x=0.0, y=0.0, inTangentY=0.0, outTangentY=0.0):
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


class HermiteCurve(object):
    def __init__(self):
        self.keys = []

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
        ttt2 = ttt + ttt
        tt2 = tt + tt
        tt3 = tt2 + tt
        h00t = ttt2 - tt3 + 1.0
        h10t = ttt - tt2 + t
        h01t = tt3 - ttt2
        h11t = ttt - tt
        return (h00t * prev.y +
                h10t * prev.outTangentY +
                h11t * next.inTangentY +
                h01t * next.y)


class KeySelection(dict):
    # dict of HermiteKey objects and bitmask of (point, intangent, outtangent)
    pass


class CurveView(QWidget):
    def __init__(self, parent=None):
        super(CurveView, self).__init__(parent)

        self.testCurve = HermiteCurve()
        self.testCurve.keys.append(HermiteKey(0.0, 0.0, 0.0, 0.0))
        k1 = HermiteKey(1.0, 1.0, 0.0, 0.0)
        self.testCurve.keys.append(k1)
        k2 = HermiteKey(2.0, 0.0, 0.0, 0.0)
        self.testCurve.keys.append(k2)
        k3 = HermiteKey(4.0, 1.0, 0.0, 0.0)
        self.testCurve.keys.append(k3)
        k4 = HermiteKey(6.0, 0.0, 0.0, 1.0)
        self.testCurve.keys.append(k4)
        k5 = HermiteKey(7.0, 1.0, 1.0, -1.0)
        self.testCurve.keys.append(k5)
        self.testCurve.keys.append(HermiteKey(8.0, 0.0, -1.0, 1.0))
        self.testCurve.keys.append(HermiteKey(12.0, 1.0, 1.0, 0.0))

        self.selectionModel = KeySelection()
        self.selectionModel[k1] = 1  # just point selected
        self.selectionModel[k2] = 1 << 1  # just in tangent selected
        self.selectionModel[k3] = 1 << 2 | 1  # out tangent and key selected
        self.selectionModel[k4] = 1 << 2 | 1 << 1 | 1  # all selected
        self.selectionModel[k5] = 1 << 1 | 1  # in tangent and key selected

        self.undoStack = QUndoStack()
        self.undoStack.createUndoAction(self).setShortcut(QKeySequence('Ctrl+Z'))

        self.action = None

        self.left = -1.0
        self.right = 13.0

        self.top = 2.0
        self.bottom = -1.0

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

    def __tangentEndPoint(self, src, dst, wt):
        TANGENT_LENGTH = 20.0
        x0, y0 = self.uToPx(src.x, src.y)
        x1, y1 = self.uToPx(dst.x, dst.y)
        dx = x1 - x0
        dy = (y1 - y0) * wt
        f = TANGENT_LENGTH / ((dx * dx + dy * dy) ** 0.5)
        x1, y1 = x0 + dx * f, y0 + dy * f
        return x1, y1

    def __drawTangent(self, painter, isSelected, src, dst, wt):
        # selection
        if isSelected:
            painter.setPen(Qt.white)
        else:
            painter.setPen(Qt.magenta)

        x0, y0 = self.uToPx(src.x, src.y)
        x1, y1 = self.__tangentEndPoint(src, dst, wt)
        painter.drawLine(x0, y0, x1, y1)
        painter.drawRect(x1 - 1, y1 - 1, 2, 2)

    def itemsAt(self, x, y, w, h):
        for i, key in enumerate(self.testCurve.keys):
            kx, ky = self.uToPx(key.x, key.y)
            if x <= kx <= x + w and y < ky <= y + h:
                yield key, 1

            if key not in self.selectionModel:
                # key or tangent must be selected for tangents to be visible
                continue

            # in tangent
            if i > 0:
                kx, ky = self.__tangentEndPoint(key, self.testCurve.keys[i - 1], key.inTangentY)
                if x <= kx <= x + w and y < ky <= y + h:
                    yield key, 1 << 1

            # out tangent
            if i < len(self.testCurve.keys) - 1:
                kx, ky = self.__tangentEndPoint(key, self.testCurve.keys[i + 1], key.outTangentY)
                if x <= kx <= x + w and y < ky <= y + h:
                    yield key, 1 << 2

    def paintEvent(self, event):
        painter = QPainter(self)
        ppt = None

        painter.fillRect(QRect(0, 0, self.width(), self.height()), QColor(40, 40, 40, 255))

        # paint evaluated data
        for x in xrange(0, self.width(), 4):
            t = self.xToT(x)
            y = self.vToY(self.testCurve.evaluate(t))
            pt = QPoint(x, y)
            if x:
                painter.drawLine(ppt, pt)
            ppt = pt

        # paint key points
        for i, key in enumerate(self.testCurve.keys):
            # if key is selected, paint tangents
            selectionState = self.selectionModel.get(key, 0)

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
                self.__drawTangent(painter, selectionState & (1 << 1), key, self.testCurve.keys[i - 1], key.inTangentY)

            # out tangent
            if i < len(self.testCurve.keys) - 1:
                self.__drawTangent(painter, selectionState & (1 << 2), key, self.testCurve.keys[i + 1], key.outTangentY)

        if self.action is not None:
            self.action.draw(painter)

    def mousePressEvent(self, event):
        self.action = MarqueeAction(self, self.selectionModel)
        if self.action.mousePressEvent(event):
            self.repaint()

    def mouseReleaseEvent(self, event):
        if self.action:
            if self.action.mouseReleaseEvent(self.undoStack):
                self.action = None
                self.repaint()
                return
            self.action = None

    def mouseMoveEvent(self, event):
        if self.action:
            if self.action.mouseMoveEvent(event):
                self.repaint()


class MarqueeAction(QUndoCommand):
    def __init__(self, view, selectionDict):
        super(MarqueeAction, self).__init__('Selection change')
        self.view = view
        self.selection = selectionDict
        self.restore = ({}, [])
        self.apply = ({}, [])

    def redo(self):
        self.selection.update(self.apply[0])
        for remove in self.apply[1]:
            del self.selection[remove]

    def undo(self):
        self.selection.update(self.restore[0])
        for remove in self.restore[1]:
            del self.selection[remove]

    def mousePressEvent(self, event):
        self.start = event.pos()
        self.end = event.pos()
        self.mode = event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier)

    def _rect(self):
        x0, x1 = self.start.x(), self.end.x()
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = self.start.y(), self.end.y()
        y0, y1 = min(y0, y1), max(y0, y1)
        return x0, y0, x1 - x0, y1 - y0

    def mouseReleaseEvent(self, undoStack):
        # TODO: Mimic maya? when mask is tangent, always deselect key; when selecting, first attempt to select keys, if no keys found then attempt to select tangents

        # TODO: Split this up per mode into separate functions, no need to test the modifier for each itemAt, see if we can decouple from the class

        def _addToApply0(apply0, key, existing, mask):
            apply0[key] = apply0.setdefault(key, existing) | mask

        def _removeFromApply0(apply0, key, existing, mask):
            apply0[key] = apply0.setdefault(key, existing) & (~mask)

        # build apply state
        x, y, w, h = self._rect()

        # creating new selection, remove everything
        if self.mode == Qt.NoModifier:
            for key in self.selection:
                self.apply[0][key] = 0

        for key, mask in self.view.itemsAt(x, y, w, h):
            # creating new selection
            if self.mode == Qt.NoModifier:
                # overwrite removed elements with only selected elements
                _addToApply0(self.apply[0], key, self.selection.get(key, 0), mask)

            # add only
            if self.mode in (Qt.ControlModifier | Qt.ShiftModifier, Qt.ShiftModifier):
                # make sure value is new to selection & register for selection
                if key not in self.selection or not (self.selection[key] & mask):
                    _addToApply0(self.apply[0], key, self.selection.get(key, 0), mask)

            # remove only
            if self.mode in (Qt.ControlModifier, Qt.ShiftModifier):
                # make sure value exists in selection & mask out the element to remove
                if key in self.selection and self.selection[key] & mask:
                    _removeFromApply0(self.apply[0], key, self.selection[key], mask)

        # finalize apply state
        for key, value in self.apply[0].iteritems():
            if value == 0:
                # all elements deselected, register for removal
                self.apply[1].append(key)

        for key in self.apply[1]:
            del self.apply[0][key]

        # cache restore state
        for addOrModify in self.apply[0]:
            if addOrModify in self.selection:
                # is modification
                self.restore[0][addOrModify] = self.selection[addOrModify]
            else:
                self.restore[1].append(addOrModify)

        for remove in self.apply[1]:
            self.restore[0][remove] = self.selection[remove]

        undoStack.push(self)
        return True

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        return True

    def draw(self, painter):
        x, y, w, h = self._rect()
        painter.setPen(QColor(0, 160, 255, 255))
        painter.setBrush(QColor(0, 160, 255, 64))
        painter.drawRect(x, y, w, h)


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


class Clip(ItemRow):
    def __init__(self, name, loopMode):
        super(Clip, self).__init__(name, loopMode)
        self.__dict__['curves'] = OrderedDict()
        self.__dict__['textures'] = OrderedDict()

    @classmethod
    def properties(cls):
        return ClipManager.columnNames()


class Label(object):
    """ Utiliy to display a non-editable string in the ItemRow system. """

    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


class Event(ItemRow):
    def __init__(self, name, clip, start=0.0, end=1.0, speed=1.0, roll=0.0):
        super(Event, self).__init__(name, Label(''), clip, start, end, end - start, speed, roll)

    def propertyChanged(self, index):
        START_INDEX = 3
        END_INDEX = 4
        DURATION_INDEX = 5

        if index == START_INDEX:
            self.end = self.start + self.duration
        elif index == END_INDEX:
            self.duration = self.end - self.start
        elif index == DURATION_INDEX:
            self.end = self.start + self.duration

    @classmethod
    def properties(cls):
        return ShotManager.columnNames()


class Shot(Event):
    def __init__(self, name, sceneName, clip, start=0.0, end=1.0, speed=1.0, roll=0.0):
        # intentionally calling super of base
        super(Event, self).__init__(name, Label(sceneName), clip, start, end, end - start, speed, roll)


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


class ClipManager(NamedColums):
    @staticmethod
    def columnNames():
        return 'name', 'loopMode'


class ShotManager(NamedColums):
    def __init__(self, parent=None):
        super(ShotManager, self).__init__(parent)
        self.model().itemChanged.connect(self.__fwdItemChanged)

    # def dataChanged(self, tl, br):
    #    for y in xrange(tl.row(), br.row() + 1):
    #        rowObj = self.model().item(y).data()
    #        for x in xrange(tl.column(), br.column() + 1):
    #            rowObj.propertyChanged(x)

    def __fwdItemChanged(self, item):
        self.model().item(item.row()).data().propertyChanged(item.column())

    @staticmethod
    def columnNames():
        return 'name', 'scene', 'clip', 'start', 'end', 'duration', 'speed', 'roll'


class _TrackManager(object):
    def __init__(self):
        self.tracks = []

    def trackForItem(self, start, end):
        for i, track in enumerate(self.tracks):
            for eventStart, eventEnd in track:
                if eventStart < end and eventEnd > start:
                    continue
                # free space found, register event and return where
                track.append((start, end))
                return i
        # new track needed
        self.tracks.append([(start, end)])
        return len(self.tracks) - 1


class EventTimeline(QWidget):
    def __init__(self, model):
        super(EventTimeline, self).__init__()
        self.model = model
        model.dataChanged.connect(self.repaint)
        self.cameraStart = 0.0
        self.cameraEnd = 10.0

    def paintEvent(self, event):
        trackHeight = 16.0
        scaleX = self.width() / (self.cameraEnd - self.cameraStart)
        eventRects = []
        # layout items in model
        shotTracks = _TrackManager()
        otherTracks = _TrackManager()
        for row in xrange(self.model.rowCount()):
            pyObj = self.model.item(row, 0).data()
            isShot = isinstance(pyObj, Shot)
            manager = shotTracks if isShot else otherTracks
            x = (pyObj.start - self.cameraStart) * scaleX
            w = (pyObj.end - self.cameraStart) * scaleX - x
            y = trackHeight * manager.trackForItem(x, x + w)
            h = trackHeight
            eventRects.append((isShot, pyObj.name, pyObj.color, QRect(x, y, w, h)))
        offsetY = len(shotTracks.tracks) * trackHeight
        painter = QPainter(self)
        for isShot, name, color, rect in eventRects:
            if isShot:
                rect.moveTop(offsetY)
            painter.fillRect(rect, color)
            painter.drawText(rect, 0, name)


def run():
    a = QApplication([])

    w = CurveView()
    w.show()
    a.exec_()
    return

    s = QSplitter(Qt.Vertical)

    w = ClipManager()
    clip0 = Clip('New Clip', ELoopMode('Clamp'))
    w.model().appendRow(clip0.items)
    s.addWidget(w)

    curve = Curve()
    curve.addKeyWithTangents(-1.0, 0.0, 0.0, 1.0, 1.0, 0.0, True, Key.TANGENT_LINEAR)
    curve.addKeyWithTangents(-1.0, 0.0, 1.0, 1.0, 1.0, 0.0, True, Key.TANGENT_LINEAR)
    clip0.curves['t.x'] = curve

    curve = Curve()
    curve.addKeyWithTangents(-1.0, 0.0, 0.0, 1.0, 1.0, 0.0, True, Key.TANGENT_LINEAR)
    curve.addKeyWithTangents(-1.0, 0.0, 1.0, 0.0, 1.0, 0.0, True, Key.TANGENT_LINEAR)
    clip0.curves['t.y'] = curve

    curve = Curve()
    curve.addKeyWithTangents(-1.0, 0.0, 0.0, 0.0, 1.0, 0.0, True, Key.TANGENT_LINEAR)
    curve.addKeyWithTangents(-1.0, 0.0, 1.0, 1.0, 1.0, 0.0, True, Key.TANGENT_LINEAR)
    clip0.curves['t.z'] = curve

    w = ShotManager()
    w.model().appendRow(Shot('New Shot', 'Scene 1', clip0, 0.0, 4.0, 1.0, 0.0).items)
    w.model().appendRow(Event('New event', clip0, 0.0, 1.0, 1.0, 0.0).items)
    w.model().appendRow(Event('New event', clip0, 1.0, 2.0, 0.5, 0.0).items)
    w.model().appendRow(Event('New event', clip0, 2.0, 4.0, 0.25, 0.0).items)
    s.addWidget(w)

    w = EventTimeline(w.model())
    s.addWidget(w)

    s.show()
    a.exec_()


if __name__ == '__main__':
    run()
