from __future__ import annotations
from typing import Any, Optional, TYPE_CHECKING

from animationgraph.curveactions import RemappedEvent
from qt import *

if TYPE_CHECKING:
    from animationgraph.curvedata import Key
    from animationgraph.curveview import CurveView


class SelectedKey:
    def __init__(self, row: int, index: int):
        self.__row = row
        self.__index = index

    def row(self) -> int:
        return self.__row

    def index(self) -> int:
        return self.__index


class Selection:
    """
    Helper class for managing the set of selected keys, or their tangents.

    All items in __keys are of type SelectedKey
    """
    KEYS, IN_TANGENT, OUT_TANGENT = range(3)

    def __init__(self) -> None:
        self.__keys: list[SelectedKey] = []
        self.__selectionType = Selection.KEYS
        self.__model: Optional[QStandardItemModel] = None

    def setModel(self, model: QStandardItemModel) -> None:
        self.__model = model

    def clear(self) -> None:
        self.__keys = []
        self.__selectionType = Selection.KEYS

    def keys(self) -> list[Key]:
        if self.__selectionType != Selection.KEYS:
            return []
        result = []
        for selectedKey in self.__keys:
            assert self.__model is not None
            result.append(self.__model.item(selectedKey.row()).data()[selectedKey.index()])
        return result

    def isKeySelected(self, row: int, index: int) -> bool:
        if self.__selectionType != Selection.KEYS:
            return False
        for selectedKey in self.__keys:
            if selectedKey.row() == row and selectedKey.index() == index:
                return True
        return False

    # TODO: Bad naming, select and deselect, not add and delete
    def addKey(self, row: int, index: int) -> None:
        # Reset selection if we were selecting a tangent
        if self.__selectionType != Selection.KEYS:
            self.__keys = []
        self.__selectionType = Selection.KEYS
        self.__keys.append(SelectedKey(row, index))

    def deleteKey(self, row: int, index: int) -> None:
        # Reset selection if we were selecting a tangent
        if self.__selectionType != Selection.KEYS:
            self.__keys = []
        self.__selectionType = Selection.KEYS

        for selectedKey in self.__keys:
            if selectedKey.row() == row and selectedKey.index() == index:
                self.__keys.remove(selectedKey)
                return


class MarqueeSelectAction:
    """ Rectangle selection with modifier support.

    none: clear & select
    shift: toggle
    ctrl: deselect
    ctrl + shift: add
    """

    def __init__(self, event: RemappedEvent, parent: CurveView) -> None:
        self.__start = event.pos()
        self.__cursor = event.pos()
        self.__screenSpaceStart = event.sourceEvent().pos()
        self.__screenSpaceCursor = event.sourceEvent().pos()
        self.__parent = parent
        self.__shift = event.modifiers() & Qt.KeyboardModifier.ShiftModifier == Qt.KeyboardModifier.ShiftModifier
        self.__ctrl = event.modifiers() & Qt.KeyboardModifier.ControlModifier == Qt.KeyboardModifier.ControlModifier

    def update(self, event: RemappedEvent) -> None:
        self.__cursor = event.pos()
        self.__screenSpaceCursor = event.sourceEvent().pos()

    def finalize(self, _: Any) -> None:
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

    def paint(self, painter: QPainter) -> None:
        x, y, x2, y2 = self.__screenSpaceStart.x(), self.__screenSpaceStart.y(), self.__screenSpaceCursor.x(), self.__screenSpaceCursor.y()
        rect = min(x, x2), min(y, y2), abs(x2 - x), abs(y2 - y)
        painter.setPen(QPen(QColor.fromRgb(120, 122, 117), 1, Qt.DashLine))
        painter.drawRect(QRectF(*rect))        
