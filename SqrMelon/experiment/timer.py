import icons
from qtutil import *


class Time(object):
    def __init__(self, time=0.0):
        self.changed = Signal()
        self._time = time

    @property
    def time(self):
        return self._time

    @time.setter
    def time(self, time):
        self._time = time
        self.changed.emit()


def drawPlayhead(painter, x, height):
    painter.setPen(Qt.red)
    painter.drawLine(x, 16, x, height)
    painter.setPen(Qt.darkRed)
    painter.drawLine(x + 1, 0, x + 1, height)
    painter.drawPixmap(x - 4, 0, icons.getImage('playhead'))
