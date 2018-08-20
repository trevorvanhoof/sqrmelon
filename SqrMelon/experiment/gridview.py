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

    def mouseReleaseEvent(self, undoStack):
        pass

    def draw(self, painter):
        pass


def zoom(pivotUnits, viewRect, hSteps, vSteps, baseValues=None):
    if baseValues is None:
        baseValues = viewRect.left, viewRect.right, viewRect.top, viewRect.bottom

    cx, cy = pivotUnits
    extents = [baseValues[0] - cx, baseValues[1] - cx, baseValues[2] - cy, baseValues[3] - cy]

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

    viewRect.set(cx + extents[0], cx + extents[1], cy + extents[2], cy + extents[3])


class ViewZoomAction(DirectionalAction):
    def __init__(self, viewRect, pixelSize, reproject, mask):
        super(ViewZoomAction, self).__init__(reproject, mask)
        self.__rect = viewRect
        self.__pixelSize = pixelSize
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

        zoom(self._dragStartU, self.__rect, dx, dy, self.__baseValues)

        return False

    def mouseReleaseEvent(self, undoStack):
        pass


class ViewRect(object):
    def __init__(self, left=-1.0, right=1.0, top=1.0, bottom=-1.0):
        self.changed = Signal()
        self._left = left
        self._right = right
        self._top = top
        self._bottom = bottom

    def set(self, left, right, top, bottom):
        self._left = left
        self._right = right
        self._top = top
        self._bottom = bottom
        self.changed.emit()

    @property
    def left(self):
        return self._left

    @left.setter
    def left(self, left):
        if self._left == left:
            return
        self._left = left
        self.changed.emit()

    @property
    def right(self):
        return self._right

    @right.setter
    def right(self, right):
        if self._right == right:
            return
        self._right = right
        self.changed.emit()

    @property
    def top(self):
        return self._top

    @top.setter
    def top(self, top):
        if self._top == top:
            return
        self._top = top
        self.changed.emit()

    @property
    def bottom(self):
        return self._bottom

    @bottom.setter
    def bottom(self, bottom):
        if self._bottom == bottom:
            return
        self._bottom = bottom
        self.changed.emit()

    @property
    def width(self):
        return self.right - self.left

    @property
    def height(self):
        return self.top - self.bottom


class GridView(QWidget):
    # TODO: Cursor management
    CELL_SIZE_MAX_PX = 80
    def __init__(self, parent=None, mask=3):
        super(GridView, self).__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self._viewRect = ViewRect()
        self._viewRect.changed.connect(self.repaint)
        self._action = None
        # bitmask that says whether we are horizontal (0b01), vertical (0b10) or 2D (0b11)
        assert mask in (1, 2, 3)
        self._mask = mask

    # mapping functions
    def xToT(self, x):
        return (x / float(self.width())) * self._viewRect.width + self._viewRect.left

    def tToX(self, t):
        return ((t - self._viewRect.left) / self._viewRect.width) * self.width()

    def yToV(self, y):
        return (y / float(self.height())) * -self._viewRect.height + self._viewRect.top

    def vToY(self, v):
        return ((v - self._viewRect.top) / -self._viewRect.height) * self.height()

    def uToPx(self, t, v):
        return self.tToX(t), self.vToY(v)

    def pxToU(self, x, y):
        return self.xToT(x), self.yToV(y)

    @property
    def cellSize(self):
        """
        Calculate the size (in time-units) of a grid-cell
        """
        view = self._viewRect.right - self._viewRect.left
        cellSize = abs(view) / (float(self.width()) / float(self.CELL_SIZE_MAX_PX))
        cellSize = min(pow(2.0, round(log(cellSize, 2.0))), pow(4.0, round(log(cellSize, 4.0))),
                       pow(8.0, round(log(cellSize, 8.0))))

        return cellSize

    def iterAxis(self, pixels, start, end, textBoundsMin, textBoundsMax, uToPx):
        view = end - start
        cellSize = self.cellSize
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

        if self._mask & 1:
            textBoundsMin = painter.fontMetrics().height()
            textBoundsMax = self.height()
            if self._mask == 1:
                textBoundsMin = textBoundsMax
            for x, y, label, color in self.iterAxis(self.width(), self._viewRect.left, self._viewRect.right, textBoundsMin, textBoundsMax, self.vToY):
                painter.setPen(color)
                painter.drawLine(x, 0, x, self.height())
                painter.setPen(Qt.black)
                painter.drawText(x + 2, y - 2, label)

        if self._mask & 2:
            textBoundsMin = 0.0
            textBoundsMax = self.width() - painter.fontMetrics().width('-0.000')
            if self._mask == 2:
                textBoundsMax = textBoundsMin
            for x, y, label, color in self.iterAxis(self.height(), self._viewRect.top, self._viewRect.bottom, textBoundsMin, textBoundsMax, self.tToX):
                painter.setPen(color)
                painter.drawLine(0, x, self.width(), x)
                painter.setPen(Qt.black)
                painter.drawText(y + 2, x - 2, label)

    def wheelEvent(self, event):
        # zoom
        cx, cy = self.pxToU(event.x(), event.y())
        d = -event.delta()
        dx, dy = 0, 0
        if self._mask & 1:
            dx = d
        if self._mask & 2:
            dy = d
        zoom((cx, cy), self._viewRect, dx, dy)

    def mousePressEvent(self, event):
        # pan
        if event.button() == Qt.RightButton:
            self._action = ViewZoomAction(self._viewRect, self.size(), self.pxToU, self._mask)
        else:
            self._action = ViewPanAction(self._viewRect, self.size())

        if self._action.mousePressEvent(event):
            self.repaint()

    def mouseReleaseEvent(self, event):
        self._action = None

    def mouseMoveEvent(self, event):
        if self._action:
            if self._action.mouseMoveEvent(event):
                self.repaint()


if __name__ == '__main__':
    a = QApplication([])
    w = GridView(mask=1)
    w.show()
    a.exec_()
