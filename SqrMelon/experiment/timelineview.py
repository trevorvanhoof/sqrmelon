from experiment.model import Shot
from qtutil import *
import icons


class GraphicsItemEvent(object):
    trackHeight = 24
    handleWidth = 8
    padding = (4, 4, 4, 4)
    iconSize = 16

    _ico = None

    @classmethod
    def iconName(cls):
        return 'Curves'

    def __init__(self, event, x, width):
        self.event = event
        self.rect = QRect(x,
                          event.track * GraphicsItemEvent.trackHeight,
                          width,
                          GraphicsItemEvent.trackHeight)
        self.iconRect = QRect(x, self.rect.y() + (self.rect.height() - GraphicsItemShot.iconSize) / 2, GraphicsItemShot.iconSize, GraphicsItemShot.iconSize)
        self.textRect = self.rect.adjusted(*GraphicsItemEvent.padding)
        self.textRect.setLeft(x + GraphicsItemShot.iconSize + GraphicsItemEvent.padding[0])
        self.__mouseOver = False
        if self.__class__._ico is None:
            self.__class__._ico = icons.getImage(self.iconName())

    def paint(self, painter):
        painter.fillRect(self.rect, self.event.color)
        highlightColor = QColor(255, 255, 64, 128)
        if self.__mouseOver == 3:
            painter.fillRect(self.rect, highlightColor)
        elif self.__mouseOver == 1:
            painter.fillRect(QRect(self.rect.x(), self.rect.y(), GraphicsItemEvent.handleWidth, self.rect.height()), highlightColor)
        elif self.__mouseOver == 2:
            painter.fillRect(QRect(self.rect.right() - GraphicsItemEvent.handleWidth + 1, self.rect.y(), GraphicsItemEvent.handleWidth, self.rect.height()), highlightColor)
        painter.drawText(self.textRect, 0, self.event.name)
        painter.drawPixmap(self.iconRect, self._ico)

    def focusOutEvent(self):
        dirty = self.__mouseOver != 0
        self.__mouseOver = 0
        return dirty

    def mouseMoveEvent(self, pos):
        mouseOver = self.rect.adjusted(0, 0, -1, -1).contains(pos)

        if mouseOver:
            state = 3
            if self.rect.width() > GraphicsItemEvent.handleWidth * 3:
                lx = pos.x() - self.rect.x()
                if lx < GraphicsItemEvent.handleWidth:
                    state = 1
                elif lx > self.rect.width() - GraphicsItemEvent.handleWidth:
                    state = 2
        else:
            state = 0

        if state != self.__mouseOver:
            self.__mouseOver = state
            return True


class GraphicsItemShot(GraphicsItemEvent):
    @classmethod
    def iconName(cls):
        return 'Film Strip'


class TimelineView(QWidget):
    def __init__(self, model):
        super(TimelineView, self).__init__()
        self.__model = model
        model.dataChanged.connect(self.layout)

        self.__cameraStart = 0.0
        self.__cameraEnd = 5.0
        self.setMouseTracking(True)
        self.__graphicsItems = []

        self.layout()

    def layout(self):
        del self.__graphicsItems[:]
        scaleX = self.width() / (self.__cameraEnd - self.__cameraStart)
        for row in xrange(self.__model.rowCount()):
            pyObj = self.__model.item(row, 0).data()
            x = round((pyObj.start - self.__cameraStart) * scaleX)
            w = round((pyObj.end - self.__cameraStart) * scaleX - x)
            isShot = isinstance(pyObj, Shot)
            if isShot:
                item = GraphicsItemShot(pyObj, x, w)
            else:
                item = GraphicsItemEvent(pyObj, x, w)
            self.__graphicsItems.append(item)
        self.repaint()

    def mouseMoveEvent(self, event):
        if event.button():
            return
        dirty = False
        pos = event.pos()
        for item in self.__graphicsItems:
            dirty = dirty or item.mouseMoveEvent(pos)
        if dirty:
            self.repaint()

    def leaveEvent(self, event):
        dirty = False
        for item in self.__graphicsItems:
            dirty = dirty or item.focusOutEvent()
        if dirty:
            self.repaint()

    def paintEvent(self, event):
        painter = QPainter(self)
        for item in self.__graphicsItems:
            item.paint(painter)
