import icons
from animationgraph.curvedata import Curve, Key
from qtutil import *
from collections import OrderedDict
from util import randomColor


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
            if isinstance(value, (float, int, bool, basestring)):
                value = type(value)
            else:
                items[-1].setEditable(False)
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
            if self.items[0].row() == 0 and index == 4: print item.text(), data
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
        print attr, value
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


class Event(ItemRow):
    def __init__(self, name, clip, start=0.0, end=1.0, speed=1.0, roll=0.0):
        super(Event, self).__init__(name, '', clip, start, end, end - start, speed, roll)

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
        super(Event, self).__init__(name, sceneName, clip, start, end, end - start, speed, roll)


class ClipManager(QTableView):
    def __init__(self, parent=None):
        super(ClipManager, self).__init__(parent)
        self.setModel(QStandardItemModel())

    @staticmethod
    def columnNames():
        return 'name', 'loopMode'


class ShotManager(QTableView):
    def __init__(self, parent=None):
        super(ShotManager, self).__init__(parent)
        self.setModel(QStandardItemModel())

    def dataChanged(self, tl, br):
        for y in xrange(tl.row(), br.row() + 1):
            rowObj = self.model().item(y).data()
            for x in xrange(tl.column(), br.column() + 1):
                rowObj.propertyChanged(x)

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
    clip0 = Clip('New Clip', 'Clamped')
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
