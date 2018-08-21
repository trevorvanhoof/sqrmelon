from qtutil import *

from commands import ConnectionEdit, MoveNode


class CreateConnectionAction(object):
    def __init__(self, plug, plugAt, triggerRepaint):
        super(CreateConnectionAction, self).__init__()
        self.__plug = plug
        self.__drag = None
        self.__over = None
        self.__plugAt = plugAt
        self._triggerRepaint = triggerRepaint

    def mousePressEvent(self, event):
        pass

    def mouseMoveEvent(self, event):
        self.__drag = event.pos()
        self.__over = self.__plugAt(event.pos())
        return True

    def mouseReleaseEvent(self, undoStack):
        undoStack.push(ConnectionEdit(self.__plug, self.__over, self._triggerRepaint))
        return True

    def draw(self, painter):
        if self.__drag is not None:
            painter.drawLine(self.__plug.portRect.center(), self.__drag)
        painter.setPen(Qt.NoPen)
        painter.setBrush(Qt.green)
        if self.__over is not None:
            painter.drawEllipse(self.__over.portRect)
        painter.drawEllipse(self.__plug.portRect)


class DragNodeAction(object):
    def __init__(self, node, triggerRepaint):
        self.__restore = node.x, node.y
        self.__node = node
        self.__dragStart = None
        self.__triggerRepaint = triggerRepaint

    def mousePressEvent(self, event):
        self.__dragStart = event.pos()

    def mouseMoveEvent(self, event):
        delta = event.pos() - self.__dragStart
        x = self.__restore[0] + delta.x()
        y = self.__restore[1] + delta.y()
        self.__node.setPosition(x, y)
        return True

    def mouseReleaseEvent(self, undoStack):
        undoStack.push(MoveNode(self.__node, self.__restore, self.__triggerRepaint))

    def draw(self, painter):
        pass
