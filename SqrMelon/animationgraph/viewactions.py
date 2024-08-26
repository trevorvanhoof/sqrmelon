from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from animationgraph.curveactions import RemappedEvent
from qt import *

if TYPE_CHECKING:
    from curveview import CurveViewCamera, Float4


class CameraUndoCommand(QUndoCommand):
    pass


class CameraFrameAction(CameraUndoCommand):
    """Snaps the camera to the given region."""
    def __init__(self, camera: CurveViewCamera, region: Float4) -> None:
        super(CameraFrameAction, self).__init__('FrameCamera')
        self.__restoreRegion = camera.region()
        self.__camera = camera
        self.__region = region

    def undo(self) -> None:
        self.__camera.setRegion(*self.__restoreRegion)

    def redo(self) -> None:
        self.__camera.setRegion(*self.__region)


class CameraZoomAction(CameraUndoCommand):
    def __init__(self, event: RemappedEvent, widgetSize: QSize, camera: CurveViewCamera) -> None:
        super(CameraZoomAction, self).__init__('ZoomCamera')
        self.__camera = camera
        self.__start = event.x(), event.y()
        # self.__widgetSize = widgetSize.width(), widgetSize.height()
        self.__restoreRegion = camera.region()
        self.__singleAxis = event.modifiers() & Qt.KeyboardModifier.ShiftModifier == Qt.KeyboardModifier.ShiftModifier
        self.__cursorOverride = False
        self.__ignoredAxis: Optional[int] = None
        self.__zoomFactor: list[float] = [0.0, 0.0]
        self.__zoomStrength = 128.0
        self.__range = event.x() / float(widgetSize.width()), event.y() / float(widgetSize.height())
        self.__sceneAnchor = self.__range[0] * self.__restoreRegion[2] + self.__restoreRegion[0], self.__range[1] * self.__restoreRegion[3] + self.__restoreRegion[1]

    def _computeDelta(self, event: RemappedEvent) -> None:
        delta = [event.x() - self.__start[0], event.y() - self.__start[1]]
        self.__zoomFactor = [delta[0] / float(self.__restoreRegion[2]), delta[1] / float(self.__restoreRegion[3])]
        ax = abs(delta[0])
        ay = abs(delta[1])
        if self.__singleAxis:
            if self.__ignoredAxis is None:
                if ax > ay:
                    self.__ignoredAxis = 1
                    self.__cursorOverride = True
                    QApplication.setOverrideCursor(Qt.CursorShape.SizeHorCursor)
                else:
                    self.__ignoredAxis = 0
                    self.__cursorOverride = True
                    QApplication.setOverrideCursor(Qt.CursorShape.SizeVerCursor)
            self.__zoomFactor[self.__ignoredAxis] = 0.0
        else:
            # Uniform scaling!
            if abs(self.__zoomFactor[0]) > abs(self.__zoomFactor[1]):
                self.__zoomFactor[1] = self.__zoomFactor[0]
            else:
                self.__zoomFactor[0] = self.__zoomFactor[1]

            if not self.__cursorOverride:
                self.__cursorOverride = True
                QApplication.setOverrideCursor(Qt.CursorShape.SizeAllCursor)

    def _apply(self) -> None:
        if self.__ignoredAxis != 0:
            w = self.__restoreRegion[2] * (self.__zoomStrength ** -self.__zoomFactor[0])
            w = max(0.01, w)
            # Zoom from the center
            x = self.__restoreRegion[0] + 0.5 * self.__restoreRegion[2] - w * 0.5
        else:
            w = self.__restoreRegion[2]
            x = self.__restoreRegion[0]

        if self.__ignoredAxis != 1:
            h = self.__restoreRegion[3] * (self.__zoomStrength ** -self.__zoomFactor[1])
            h = max(0.01, h)
            # Zoom from the center
            y = self.__restoreRegion[1] + 0.5 * self.__restoreRegion[3] - h * 0.5
        else:
            h = self.__restoreRegion[3]
            y = self.__restoreRegion[1]

        self.__camera.setRegion(x, y, w, h)

    def _restore(self) -> None:
        self.__camera.setRegion(*self.__restoreRegion)

    def update(self, event: RemappedEvent) -> None:
        self._computeDelta(event)
        self._apply()

    def finalize(self, event: RemappedEvent) -> bool:
        if self.__cursorOverride:
            QApplication.restoreOverrideCursor()
        self._computeDelta(event)
        self._apply()
        return True

    def undo(self) -> None:
        self._restore()

    def redo(self) -> None:
        self._apply()


class CameraPanAction(CameraUndoCommand):
    def __init__(self, event: RemappedEvent, camera: CurveViewCamera) -> None:
        super(CameraPanAction, self).__init__('PanCamera')
        self.__camera = camera
        self.__start = event.x(), event.y()
        self.__restore = camera.position()
        self.__singleAxis = event.modifiers() & Qt.KeyboardModifier.ShiftModifier == Qt.KeyboardModifier.ShiftModifier
        self.__cursorOverride = False
        self.__ignoredAxis: Optional[int] = None
        self.__delta = [0.0, 0.0]

    def _computeDelta(self, event: RemappedEvent) -> None:
        self.__delta = [event.x() - self.__start[0], event.y() - self.__start[1]]
        ax = abs(self.__delta[0])
        ay = abs(self.__delta[1])
        if self.__singleAxis:
            if self.__ignoredAxis is None:
                if ax > ay:
                    self.__ignoredAxis = 1
                    self.__cursorOverride = True
                    QApplication.setOverrideCursor(Qt.CursorShape.SizeHorCursor)
                else:
                    self.__ignoredAxis = 0
                    self.__cursorOverride = True
                    QApplication.setOverrideCursor(Qt.CursorShape.SizeVerCursor)
            self.__delta[self.__ignoredAxis] = 0
        elif not self.__cursorOverride:
            self.__cursorOverride = True
            QApplication.setOverrideCursor(Qt.CursorShape.SizeAllCursor)

    def _apply(self) -> None:
        self.__camera.setPosition(self.__restore[0] - self.__delta[0], self.__restore[1] - self.__delta[1])

    def _restore(self) -> None:
        self.__camera.setPosition(self.__restore[0], self.__restore[1])

    def update(self, event: RemappedEvent) -> None:
        self._computeDelta(event)
        self._apply()

    def finalize(self, event: RemappedEvent) -> bool:
        if self.__cursorOverride:
            QApplication.restoreOverrideCursor()
        self._computeDelta(event)
        self._apply()
        return True

    def undo(self) -> None:
        self._restore()

    def redo(self) -> None:
        self._apply()
