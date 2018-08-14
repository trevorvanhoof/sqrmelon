from experiment.gridview import GridView
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


class TimelineView(GridView):
    def __init__(self, *models):
        super(TimelineView, self).__init__(mask=1)
        self.__models = models
        for model in models:
            model.dataChanged.connect(self.layout)

        self.setMouseTracking(True)
        self.__graphicsItems = []

        self.frameAll()
        self._viewRect.changed.connect(self.layout)
        # layout already calls repaint
        self._viewRect.changed.disconnect(self.repaint)

    def frameAll(self):
        start = float('inf')
        end = float('-inf')
        for pyObj in self.__iterAllItemRows():
            start = min(start, pyObj.start)
            end = max(end, pyObj.end)
        if start == float('inf'):
            start = 0.0
            end = 1.0
        self._viewRect.left = start
        self._viewRect.right = end

    def resizeEvent(self, event):
        self.layout()

    def __iterAllItemRows(self):
        for model in self.__models:
            for row in xrange(model.rowCount()):
                yield model.item(row, 0).data()

    def layout(self):
        del self.__graphicsItems[:]
        scaleX = self.width() / (self._viewRect.right - self._viewRect.left)
        for pyObj in self.__iterAllItemRows():
            x = round((pyObj.start - self._viewRect.left) * scaleX)
            w = round((pyObj.end - self._viewRect.left) * scaleX - x)
            isShot = isinstance(pyObj, Shot)
            if isShot:
                item = GraphicsItemShot(pyObj, x, w)
            else:
                item = GraphicsItemEvent(pyObj, x, w)
            self.__graphicsItems.append(item)
        self.repaint()

    def mouseMoveEvent(self, event):
        if self._action:
            super(TimelineView, self).mouseMoveEvent(event)
            return

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
        super(TimelineView, self).paintEvent(event)

        painter = QPainter(self)
        for item in self.__graphicsItems:
            item.paint(painter)
