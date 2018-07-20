from qtutil import *
from collections import OrderedDict
from util import randomColor


class HermiteKey(object):
    def __init__(self):
        pass


class HermiteCurve(object):
    def __init__(self):
        pass


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
