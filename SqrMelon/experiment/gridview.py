from math import log, floor, ceil

from experiment.actions import DirectionalAction
from qtutil import *


def clamp(v, n, x):
    return min(max(v, n), x)


class ViewPanAction(object):
    def __init__(self, viewRect, widgetSize):
        self.__dragStart = None
        self.__rect = viewRect
        self.__widgetSize = widgetSize

    def mousePressEvent(self, event):
        self.__dragStart = event.pos()
        self.__startPos = self.__rect.left, self.__rect.right, self.__rect.top, self.__rect.bottom

    def mouseMoveEvent(self, event):
        delta = event.pos() - self.__dragStart
        ux = delta.x() * (self.__rect.right - self.__rect.left) / float(self.__widgetSize.width())
        uy = delta.y() * (self.__rect.bottom - self.__rect.top) / float(self.__widgetSize.height())
        self.__rect.left = self.__startPos[0] - ux
        self.__rect.right = self.__startPos[1] - ux
        self.__rect.top = self.__startPos[2] - uy
        self.__rect.bottom = self.__startPos[3] - uy
        return True

    def draw(self, painter):
        pass


def zoom(pivotUnits, viewRect, hSteps, vSteps, triggerRepaint):
    cx, cy = pivotUnits
    extents = [viewRect.left - cx, viewRect.right - cx, viewRect.top - cy, viewRect.bottom - cy]

    for step in xrange(abs(hSteps)):
        if hSteps > 0:
            extents[0] *= 1.0005
            extents[1] *= 1.0005
        else:
            extents[0] /= 1.0005
            extents[1] /= 1.0005

    for step in xrange(abs(vSteps)):
        if vSteps > 0:
            extents[2] *= 1.0005
            extents[3] *= 1.0005
        else:
            extents[2] /= 1.0005
            extents[3] /= 1.0005

    viewRect.left = cx + extents[0]
    viewRect.right = cx + extents[1]
    viewRect.top = cy + extents[2]
    viewRect.bottom = cy + extents[3]

    triggerRepaint()


class ViewZoomAction(DirectionalAction):
    def __init__(self, viewRect, pixelSize, reproject, triggerRepaint):
        super(ViewZoomAction, self).__init__(reproject)
        self.__rect = viewRect
        self.__pixelSize = pixelSize
        self.__triggerRepaint = triggerRepaint
        self.__baseValues = self.__rect.left, self.__rect.right, self.__rect.top, self.__rect.bottom

    def processMouseDelta(self, event):
        dx = self._dragStartPx.x() - event.x()
        dy = self._dragStartPx.y() - event.y()
        dx = int(dx * 4000.0 / float(self.__pixelSize.width()))
        dy = int(dy * 4000.0 / float(self.__pixelSize.height()))
        if not self._mask & 1:
            dx = 0
        if not self._mask & 2:
            dy = 0

        self.__rect.left, self.__rect.right, self.__rect.top, self.__rect.bottom = self.__baseValues
        zoom(self._dragStartU, self.__rect, dx, dy, self.__triggerRepaint)


class ViewRect(object):
    def __init__(self, left=-1.0, right=1.0, top=1.0, bottom=-1.0):
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom

    @property
    def width(self):
        return self.right - self.left

    @property
    def height(self):
        return self.top - self.bottom


class GridView(QWidget):
    def __init__(self):
        super(GridView, self).__init__()
        self.view = ViewRect()
        self.action = None

    # mapping functions
    def xToT(self, x):
        return (x / float(self.width())) * self.view.width + self.view.left

    def tToX(self, t):
        return ((t - self.view.left) / self.view.width) * self.width()

    def yToV(self, y):
        return (y / float(self.height())) * -self.view.height + self.view.top

    def vToY(self, v):
        return ((v - self.view.top) / -self.view.height) * self.height()

    def uToPx(self, t, v):
        return self.tToX(t), self.vToY(v)

    def pxToU(self, x, y):
        return self.xToT(x), self.yToV(y)

    def iterAxis(self, pixels, start, end, textBoundsMin, textBoundsMax, uToPx):
        CELL_SIZE_MAX_PX = 80
        view = end - start
        cellSize = abs(view) / (float(pixels) / float(CELL_SIZE_MAX_PX))
        cellSize = min(pow(2.0, round(log(cellSize, 2.0))), pow(4.0, round(log(cellSize, 4.0))), pow(8.0, round(log(cellSize, 8.0))))
        cursor = int(ceil(start / cellSize))
        limit = int(floor(end / cellSize))
        if cursor > limit:
            cursor, limit = limit, cursor
        while cursor <= limit:
            x = int((cursor * cellSize - start) * float(pixels) / view)
            y = uToPx(0.0)
            v = cursor * cellSize
            if v == 0:
                cl = QColor(40, 40, 40)
            elif floor(v) == v:
                cl = QColor(80, 80, 80)
            else:
                cl = QColor(100, 100, 100)
            yield x, clamp(y, textBoundsMin, textBoundsMax), ('%.3f' % v).rstrip('.0') or '0', cl
            cursor += 1

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(0, 0, self.width(), self.height(), QColor(120, 120, 120))

        textBoundsMin = painter.fontMetrics().height()
        textBoundsMax = self.height()
        for x, y, label, color in self.iterAxis(self.width(), self.view.left, self.view.right, textBoundsMin, textBoundsMax, self.vToY):
            painter.setPen(color)
            painter.drawLine(x, 0, x, self.height())
            painter.setPen(Qt.black)
            painter.drawText(x + 2, y - 2, label)

        textBoundsMin = 0.0
        textBoundsMax = self.width() - painter.fontMetrics().width('-0.000')
        for x, y, label, color in self.iterAxis(self.height(), self.view.top, self.view.bottom, textBoundsMin, textBoundsMax, self.tToX):
            painter.setPen(color)
            painter.drawLine(0, x, self.width(), x)
            painter.setPen(Qt.black)
            painter.drawText(y + 2, x - 2, label)

    def wheelEvent(self, event):
        # zoom
        cx, cy = self.pxToU(event.x(), event.y())
        d = event.delta()
        zoom((cx, cy), self.view, d, d, self.repaint)

    def mousePressEvent(self, event):
        # alt for camera manip
        if event.modifiers() & Qt.AltModifier:
            # pan
            if event.button() == Qt.RightButton:
                self.action = ViewZoomAction(self.view, self.size(), self.pxToU, self.repaint)
            else:
                self.action = ViewPanAction(self.view, self.size())

        if self.action:
            if self.action.mousePressEvent(event):
                self.repaint()

    def mouseReleaseEvent(self, event):
        self.action = None

    def mouseMoveEvent(self, event):
        if self.action:
            if self.action.mouseMoveEvent(event):
                self.repaint()


if __name__ == '__main__':
    a = QApplication([])
    w = GridView()
    w.show()
    a.exec_()
