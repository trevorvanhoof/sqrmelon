from typing import Iterable, Union

from mathutil import Vec2
from animationgraph.curvedata import Curve, Key
from qtutil import *


class RemappedEvent:
    """Utility to store event data in camera-space instead of pixel-space"""

    def __init__(self, pos: QPoint, event: QMouseEvent) -> None:
        self.__pos = pos
        self.__event = event

    def pos(self) -> QPoint:
        return self.__pos

    def x(self) -> int:
        return self.__pos.x()

    def y(self) -> int:
        return self.__pos.y()

    # TODO: This looks shoddy
    def __getattr__(self, attr: str) -> Any:
        return getattr(self.__event, attr)


class DragAction(QUndoCommand):
    """Wrapper to move given set of keys & track undo-state."""

    def __init__(self,
                 event: RemappedEvent,
                 selection: Iterable[Key],
                 clickCallback: Optional[Callable],
                 scale: tuple[float, float],
                 snap: tuple[int, int]) -> None:
        super(DragAction, self).__init__('MoveKeys')
        self.__start = event.pos()
        self.__clickCallback = clickCallback  # If we didn't actually drag the data, call this to simulate a click.
        self.__singleAxis = event.modifiers() & Qt.ShiftModifier == Qt.ShiftModifier
        self.__ignoredAxis: Optional[int] = None
        self.__selection = selection
        self.__delta = 0.0, 0.0
        self.__snap = snap
        self.__restoreData = []
        self.__scale = scale
        self.__cursorOverride = False
        for key in selection:
            self.__restoreData.append(key.point())

    def _validate(self, event: RemappedEvent) -> bool:
        """
        Check if we move far enough so we don't accidentally move minute amounts.
        When shift is pressed we want to move only on 1 axis, so detect which
        direction we are dragging to set the right mode & cursor.
        """
        self.__delta = [event.x() - self.__start.x(), event.y() - self.__start.y()]
        MOVE_TOLERANCE = 6
        ax = abs(self.__delta[0]) * self.__scale[0]
        ay = abs(self.__delta[1]) * self.__scale[1]
        if ax + ay < MOVE_TOLERANCE:
            return False
        if self.__singleAxis:
            if self.__ignoredAxis is None:
                if ax > ay:
                    self.__ignoredAxis = 1
                    self.__cursorOverride = True
                    QApplication.setOverrideCursor(Qt.SizeHorCursor)
                else:
                    self.__ignoredAxis = 0
                    self.__cursorOverride = True
                    QApplication.setOverrideCursor(Qt.SizeVerCursor)
            self.__delta[self.__ignoredAxis] = 0.0
        elif not self.__cursorOverride:
            self.__cursorOverride = True
            QApplication.setOverrideCursor(Qt.SizeAllCursor)
        return True

    def _restore(self) -> None:
        """Revert key state."""
        i = 0
        for key in self.__selection:
            key.setPoint(self.__restoreData[i])
            i += 1

    def _apply(self) -> None:
        """Set key state."""
        i = 0
        for key in self.__selection:
            x = self.__restoreData[i][0] + self.__delta[0]
            y = self.__restoreData[i][1] + self.__delta[1]
            if self.__snap[0]:
                x = round(x * self.__snap[0]) / self.__snap[0]
            if self.__snap[1]:
                y = round(y * self.__snap[1]) / self.__snap[1]
            key.setPoint(Vec2(x, y))
            i += 1

    def update(self, event: RemappedEvent) -> bool:
        """Handle mouse move.

        Move keys based on initial click event & key position, so there is no error accumulation.
        """
        # drag should be implicit, so we can just validate and redraw the new state (moved or undone)
        if self._validate(event):
            self.__clickCallback = None
            self._apply()
            return True
        self._restore()
        return False

    def finalize(self, event: RemappedEvent) -> bool:
        """Handle mouse release.

        Restore cursor and trigger click if we didn't move the keys.
        """

        if self.__cursorOverride:
            QApplication.restoreOverrideCursor()
        if self.update(event):
            return True
        if self.__clickCallback:
            self.__clickCallback()
        return False

    def undo(self) -> None:
        self._restore()

    def redo(self) -> None:
        self._apply()


class DeleteAction(QUndoCommand):
    """Cache given set of keys in the undo stack and remove them upon pushing the command in the stack."""

    def __init__(self, selectionPerChannel) -> None:
        super(DeleteAction, self).__init__('DeleteKey')
        self.__selectionPerChannel = selectionPerChannel

    def redo(self) -> None:
        for key in self.__selectionPerChannel:
            key.delete()

    def undo(self) -> None:
        for key in self.__selectionPerChannel:
            key.reInsert()


class InsertKeyAction(QUndoCommand):
    def __init__(self, time: float, curves: Iterable[Curve]) -> None:
        super(InsertKeyAction, self).__init__('InsertKey')
        self.__keys: list[Key] = []
        for curve in curves:
            key = curve.keyAt(time)
            if key:
                continue
            value = curve.evaluate(time)
            k = Key(time, value, curve)
            k._Key__tangentMode = Key.TANGENT_AUTO
            self.__keys.append(k)

    def redo(self) -> None:
        for key in self.__keys:
            key.reInsert()

    def undo(self) -> None:
        for key in self.__keys:
            key.delete()


class KeyChange:
    """
    A wrapper class that looks like a Key() but in fact only changes an existing Key.
    Used by SetKeyAction in case we are setting a key at a time that already has a key.
    """

    def __init__(self, newY: float, key: Key) -> None:
        self.__newY = newY
        self.__key = key
        self.__oldY = key.value()

    def reInsert(self) -> None:
        self.__key.setValue(self.__newY)

    def delete(self) -> None:
        self.__key.setValue(self.__oldY)


class SetKeyAction(QUndoCommand):
    def __init__(self, time, curves: Iterable[Curve], values: tuple[float]) -> None:
        super(SetKeyAction, self).__init__('SetKey')
        self.__keys: list[Union[KeyChange, Key]] = []
        for i, curve in enumerate(curves):
            key = curve.keyAt(time)
            if key:
                self.__keys.append(KeyChange(values[i], key))
            else:
                self.__keys.append(Key(time, values[i], curve))

    def redo(self) -> None:
        for key in self.__keys:
            key.reInsert()

    def undo(self) -> None:
        for key in self.__keys:
            key.delete()


class EditKeyAction(QUndoCommand):
    """
    Single action supporting multiple different "setter" actions on the key data.
    Caches the given keys' initial values of the right attribute
    and sets them to the given values upon redo().
    """
    MODE_TANGENT_TYPE = 0
    MODE_TANGENT_BROKEN = 1
    MODE_TIME = 2
    MODE_VALUE = 3

    def __init__(self, keys: Iterable[Key], values: list[Union[int, float, bool]], mode: int) -> None:
        super(EditKeyAction, self).__init__()

        self.__mode: int = mode

        self.__keys: list[Key] = []
        self.__newValues: list[Union[int, float, bool]] = []
        self.__oldValues: list[Union[int, float, bool]] = []

        if mode == self.MODE_TANGENT_TYPE:
            for i, key in enumerate(keys):
                self.__oldValues.append(key.tangentMode)
                self.__newValues.append(values[i])
                self.__keys.append(key)

        elif mode == self.MODE_TANGENT_BROKEN:
            for i, key in enumerate(keys):
                self.__oldValues.append(key.tangentBroken)
                self.__newValues.append(values[i])
                self.__keys.append(key)

        elif mode == self.MODE_TIME:
            for i, key in enumerate(keys):
                self.__oldValues.append(key.time())
                self.__newValues.append(values[i])
                self.__keys.append(key)

        elif mode == self.MODE_VALUE:
            for i, key in enumerate(keys):
                self.__oldValues.append(key.value())
                self.__newValues.append(values[i])
                self.__keys.append(key)

        else:
            raise RuntimeError('Invalid key edit mode specified.')

    def isEmpty(self) -> bool:
        return not self.__keys

    def __set(self, key: Key, value: Union[int, float, bool]) -> None:
        if self.__mode == self.MODE_TANGENT_TYPE:
            key.tangentMode = value
        elif self.__mode == self.MODE_TANGENT_BROKEN:
            key.tangentBroken = value
        elif self.__mode == self.MODE_TIME:
            key.setTime(value)
        elif self.__mode == self.MODE_VALUE:
            key.setValue(value)

    def redo(self) -> None:
        for i, key in enumerate(self.__keys):
            self.__set(key, self.__newValues[i])

    def undo(self) -> None:
        for i, key in enumerate(self.__keys):
            self.__set(key, self.__oldValues[i])
