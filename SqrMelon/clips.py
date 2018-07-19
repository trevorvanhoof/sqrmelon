import icons
from animationgraph.curvedata import Curve, Key
from qtutil import *
from collections import OrderedDict
from util import randomColor


class Clip(object):
    def __init__(self, name, curves=None, textures=None):
        self.item = QStandardItem(name)

        self.curves = curves or OrderedDict()
        self.textures = textures or OrderedDict()

    def duration(self):
        duration = 0.0
        for curve in self.curves.itervalues():
            for key in curve:
                duration = max(duration, key.time())
        return duration

    @property
    def name(self):
        return self.item.text()

    def evaluate(self, time):
        data = {}
        for name in self.curves:
            value = self.curves[name].evaluate(time)
            if '.' in name:
                name, channel = name.split('.', 1)
                if name in data:
                    data[name][channel] = value
                else:
                    data[name] = {channel: value}
            else:
                assert name not in data
                data[name] = value
        for name in data:
            if isinstance(data[name], dict):
                v = data[name]
                if 'w' in v:
                    data[name] = [v['x'],
                                  v['y'],
                                  v['z'],
                                  v['w']]
                elif 'z' in v:
                    data[name] = [v['x'],
                                  v['y'],
                                  v['z']]
                elif 'y' in v:
                    data[name] = [v['x'],
                                  v['y']]
                else:
                    data[name] = [v['x']]
        return data


class Event(object):
    def __init__(self, name, clip=None, start=0.0, end=None, speed=1.0, preroll=0.0):
        end = end or clip.duration()

        self.items = [QStandardItem(name),
                      QStandardItem('<no scene>'),
                      QStandardItem(str(start)),
                      QStandardItem(str(end)),
                      QStandardItem(str(end - start)),
                      QStandardItem(str(speed)),
                      QStandardItem(str(preroll)),
                      QStandardItem(clip.name)]

        self.items[0].setData(self, Qt.UserRole + 1)
        self.items[0].setIcon(icons.get('Checked Checkbox'))

        self.clip = clip

        self._enabled = True
        self.color = QColor.fromRgb(*randomColor())

    def evaluate(self, time):
        time -= self.start
        time *= self.speed
        time -= self.preroll
        data = self.clip.evaluate(time)

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        if not value:
            self.items[0].setIcon(icons.get('Unchecked Checkbox'))
        else:
            self.items[0].setIcon(icons.get('Checked Checkbox'))

    @property
    def name(self):
        return self.items[0].text()

    @property
    def start(self):
        return float(self.items[2].text())

    @start.setter
    def start(self, value):
        strVal = str(value)
        if strVal == self.items[2].text():
            return
        self.items[2].setText(strVal)
        self.end = value + self.duration

    @property
    def end(self):
        return float(self.items[3].text())

    @end.setter
    def end(self, value):
        strVal = str(value)
        if strVal == self.items[3].text():
            return
        self.items[3].setText(strVal)
        self.duration = value - self.start

    @property
    def duration(self):
        return float(self.items[4].text())

    @duration.setter
    def duration(self, value):
        strVal = str(value)
        if strVal == self.items[4].text():
            return
        self.items[4].setText(strVal)
        self.end = value + self.start

    @property
    def speed(self):
        return float(self.items[5].text())

    @speed.setter
    def speed(self, value):
        strVal = str(value)
        if strVal == self.items[5].text():
            return
        self.items[5].setText(strVal)

    @property
    def preroll(self):
        return float(self.items[6].text())

    @preroll.setter
    def preroll(self, value):
        strVal = str(value)
        if strVal == self.items[6].text():
            return
        self.items[6].setText(strVal)


class Shot(Event):
    def __init__(self, sceneName, name, clip=None, start=0.0, end=1.0, speed=1.0, preroll=0.0):
        super(Shot, self).__init__(name, clip, start, end, speed, preroll)
        self.items[1].setText(sceneName)
        self._pinned = False

    @property
    def sceneName(self):
        return self.items[1].text()

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        self.pinned = False
        if not value:
            self.items[0].setIcon(icons.get('Unchecked Checkbox'))
        else:
            self.items[0].setIcon(icons.get('Checked Checkbox'))

    @property
    def pinned(self):
        return self._pinned

    @pinned.setter
    def pinned(self, value):
        if value:
            self.enabled = True
        self._pinned = value
        if value:
            self.items[0].setIcon(icons.get('Pin'))
        else:
            if not self._enabled:
                self.items[0].setIcon(icons.get('Unchecked Checkbox'))
            else:
                self.items[0].setIcon(icons.get('Checked Checkbox'))


class ClipEditor(QWidget):
    def __init__(self, model):
        super(ClipEditor, self).__init__()


class EventEditor(QWidget):
    def __init__(self, model):
        super(EventEditor, self).__init__()


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
            pyObj = self.model.item(row, 0).data(Qt.UserRole + 1)
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


if __name__ == '__main__':
    curves = OrderedDict()

    curve = Curve()
    curve.addKeyWithTangents(-1.0, 0.0, 0.0, 1.0, 1.0, 0.0, True, Key.TANGENT_LINEAR)
    curve.addKeyWithTangents(-1.0, 0.0, 1.0, 1.0, 1.0, 0.0, True, Key.TANGENT_LINEAR)
    curves['t.x'] = curve

    curve = Curve()
    curve.addKeyWithTangents(-1.0, 0.0, 0.0, 1.0, 1.0, 0.0, True, Key.TANGENT_LINEAR)
    curve.addKeyWithTangents(-1.0, 0.0, 1.0, 0.0, 1.0, 0.0, True, Key.TANGENT_LINEAR)
    curves['t.y'] = curve

    curve = Curve()
    curve.addKeyWithTangents(-1.0, 0.0, 0.0, 0.0, 1.0, 0.0, True, Key.TANGENT_LINEAR)
    curve.addKeyWithTangents(-1.0, 0.0, 1.0, 1.0, 1.0, 0.0, True, Key.TANGENT_LINEAR)
    curves['t.z'] = curve

    a = QApplication([])

    clipModel = QStandardItemModel()
    clip = Clip('test_clip', curves)
    clipModel.appendRow(clip.item)

    events = [Event('test_event', clip),
              Event('test_event 2', clip, 1.0, 2.0),
              Event('test_event 3', clip, 2.0, 4.0, 0.5),
              Shot('Scene01', 'test_shot', clip, 0.0, 4.0, 0.25)]
    eventModel = QStandardItemModel()
    for event in events:
        eventModel.appendRow(event.items)

    clipEditor = ClipEditor(clipModel)
    eventEditor = EventEditor(eventModel)
    eventTimeline = EventTimeline(eventModel)
    window = QMainWindow()
    widgets = QSplitter(Qt.Vertical)
    widgets.addWidget(clipEditor)
    widgets.addWidget(eventEditor)
    widgets.addWidget(eventTimeline)
    window.setCentralWidget(widgets)
    window.show()

    a.exec_()