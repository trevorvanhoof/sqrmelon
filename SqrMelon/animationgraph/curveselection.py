from pycompat import *
from qtutil import *


class SelectedKey:
    def __init__(self, row, index):
        self.__row = row
        self.__index = index

    def row(self):
        return self.__row

    def index(self):
        return self.__index


class Selection(object):
    """
    Helper class for managing the set of selected keys, or their tangents.

    All items in __keys are of type SelectedKey
    """
    KEYS, IN_TANGENT, OUT_TANGENT = range(3)

    def __init__(self):
        self.__keys = []
        self.__selectionType = Selection.KEYS
        self.__model = None

    def setModel(self, model):
        self.__model = model

    def clear(self):
        self.__keys = []
        self.__selectionType = Selection.KEYS

    def keys(self):
        if self.__selectionType != Selection.KEYS:
            return []
        result = []
        for selectedKey in self.__keys:
            result.append(self.__model.item(selectedKey.row()).data()[selectedKey.index()])
        return result

    def isKeySelected(self, row, index):
        if self.__selectionType != Selection.KEYS:
            return False
        for selectedKey in self.__keys:
            if selectedKey.row() == row and selectedKey.index() == index:
                return True
        return False

    def addKey(self, row, index):
        # Reset selection if we were selecting a tangent
        if self.__selectionType != Selection.KEYS:
            self.__keys = []
        self.__selectionType = Selection.KEYS
        self.__keys.append(SelectedKey(row, index))

    def deleteKey(self, row, index):
        # Reset selection if we were selecting a tangent
        if self.__selectionType != Selection.KEYS:
            self.__keys = []
        self.__selectionType = Selection.KEYS

        for selectedKey in self.__keys:
            if selectedKey.row() == row and selectedKey.index() == index:
                self.__keys.remove(selectedKey)
                return


class MarqueeSelectAction(object):
    """
    Rectangle selection with modifier support.
    none: clear & select
    shift: toggle
    ctrl: deselect
    ctrl + shift: add
    """

    def __init__(self, event, parent):
        self.__start = event.pos()
        self.__cursor = event.pos()
        self.__parent = parent
        self.__shift = event.modifiers() & Qt.ShiftModifier == Qt.ShiftModifier
        self.__ctrl = event.modifiers() & Qt.ControlModifier == Qt.ControlModifier

    def update(self, event):
        self.__cursor = event.pos()

    def finalize(self, _):
        x, y, x2, y2 = self.__start.x(), self.__start.y(), self.__cursor.x(), self.__cursor.y()
        bounds = min(x, x2), min(y, y2), max(x, x2), max(y, y2)
        first = True

        # start with deselecting all
        if not self.__shift and not self.__ctrl:
            self.__parent.deselectAll()

        # select items in rect
        for row, index, key in self.__parent.iterVisibleKeys():
            point = key.point()
            if bounds[0] < point.x < bounds[2] and bounds[1] < point.y < bounds[3]:
                # select
                self.__parent.select(row, index, self.__shift, self.__ctrl)
                if first:
                    if not self.__shift and not self.__ctrl:
                        self.__shift = True
                        self.__ctrl = True
                    first = False

    def paint(self, painter):
        x, y, x2, y2 = self.__start.x(), self.__start.y(), self.__cursor.x(), self.__cursor.y()
        rect = min(x, x2), min(y, y2), abs(x2 - x), abs(y2 - y)
        pen = QPen(Qt.white)
        pen.setStyle(Qt.DotLine)

        painter.setPen(Qt.black)
        painter.drawRect(QRectF(*rect))
        painter.setPen(pen)
        painter.drawRect(QRectF(*rect))
