from math import log, floor, ceil

from qtutil import *


class ViewRect(object):
    def __init__(self, left=-1.0, right=1.0, top=-1.0, bottom=1.0):
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom

    @property
    def width(self):
        return self.right - self.left

    @property
    def height(self):
        return self.bottom - self.top


class GridView(QWidget):
    def __init__(self):
        super(GridView, self).__init__()
        self.view = ViewRect()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(0, 0, self.width(), self.height(), QColor(120, 120, 120))

        CELL_SIZE_MAX_PX = 80

        cellWidth = self.view.width / (float(self.width()) / float(CELL_SIZE_MAX_PX))
        cellWidth = min(pow(2.0, round(log(cellWidth, 2.0))), pow(5.0, round(log(cellWidth, 5.0))), pow(10.0, round(log(cellWidth, 10.0))))
        cursor = int(ceil(self.view.left / cellWidth))
        limit = int(floor(self.view.right / cellWidth))
        while cursor <= limit:
            x = int((cursor * cellWidth - self.view.left) * float(self.width()) / self.view.width)
            painter.drawLine(x, 0, x, self.height())
            painter.drawText(x, self.height(), str(cursor * cellWidth))
            cursor += 1

        cellHeight = self.view.height / (float(self.height()) / float(CELL_SIZE_MAX_PX))
        cellHeight = min(pow(2.0, round(log(cellHeight, 2.0))), pow(5.0, round(log(cellHeight, 5.0))), pow(10.0, round(log(cellHeight, 10.0))))
        cursor = int(ceil(self.view.top / cellHeight))
        limit = int(floor(self.view.bottom / cellHeight))
        while cursor <= limit:
            y = int((cursor * cellHeight - self.view.top) * float(self.height()) / self.view.height)
            painter.drawLine(0, y, self.width(), y)
            # TODO: compute x at unit 0.0, then clamp so text stays on screen
            painter.drawText(0, y, str(cursor * cellWidth))
            cursor += 1


if __name__ == '__main__':
    a = QApplication([])
    w = GridView()
    w.show()
    a.exec_()
