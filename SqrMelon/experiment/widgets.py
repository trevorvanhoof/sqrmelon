from collections import OrderedDict

from experiment.actions import SelectionModelEdit
from qtutil import *
from experiment.modelbase import Shot, Clip

from experiment.delegates import NamedColums


class ClipManager(NamedColums):
    focusCurves = pyqtSignal(OrderedDict)

    def __init__(self, undoStack, parent=None):
        super(ClipManager, self).__init__(parent)
        self.__undoStack = undoStack
        self.selectionModel().selectionChanged.connect(self.__selectionChanged)

    def __selectionChanged(self, selected, deselected):
        self.__undoStack.push(SelectionModelEdit(self.selectionModel(), selected, deselected))

        rows = self.selectionModel().selectedRows()
        if rows:
            pyObj = rows[0].data(Qt.UserRole + 1).curves
        else:
            pyObj = OrderedDict()
        self.focusCurves.emit(pyObj)

    @staticmethod
    def columnNames():
        return Clip.properties()


class ShotManager(NamedColums):
    def __init__(self, parent=None):
        super(ShotManager, self).__init__(parent)
        self.model().itemChanged.connect(self.__fwdItemChanged)

    def __fwdItemChanged(self, item):
        self.model().item(item.row()).data().propertyChanged(item.column())

    @staticmethod
    def columnNames():
        return Shot.properties()


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
