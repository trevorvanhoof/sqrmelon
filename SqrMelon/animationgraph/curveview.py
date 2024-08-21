# TODO: scroll wheel zoom, zoom X and Y equally
from __future__ import annotations

import functools
import re
import time
from math import log10, floor
from typing import cast, Iterable, Optional, TYPE_CHECKING, Union

import icons
from animationgraph.curveactions import DeleteAction, DragAction, EditKeyAction, InsertKeyAction, RemappedEvent, SetKeyAction
from animationgraph.curvedata import Curve, Key
from animationgraph.curveselection import MarqueeSelectAction, Selection
from animationgraph.viewactions import CameraFrameAction, CameraPanAction, CameraUndoCommand, CameraZoomAction
from mathutil import Vec2
from projutil import gSettings
from qt import *
from qtutil import CheckBox, DoubleSpinBox, EnumBox, hlayout, QSplitterState, vlayout
from timeslider import Timer

if TYPE_CHECKING:
    from shots import Shot

Float4 = tuple[float, float, float, float]


class CurveViewCamera(QObject):
    """Camera used by the CurveView renderer & interaction."""
    regionChanged = Signal()

    def __init__(self, x: float, y: float, w: float, h: float) -> None:
        super().__init__()
        self.__visibleRegion = [x, y, w, h]

    def position(self) -> tuple[float, float]:
        return self.__visibleRegion[0], self.__visibleRegion[1]

    def setPosition(self, x: float, y: float) -> None:
        self.__visibleRegion[:2] = x, y
        self.regionChanged.emit()

    def region(self) -> Float4:
        return cast(Float4, tuple(self.__visibleRegion))

    def setRegion(self, x: float, y: float, w: float, h: float) -> None:
        self.__visibleRegion = [x, y, w, h]
        self.regionChanged.emit()


class CurveView(QWidget):
    """Graph editor.

    Renders curves & handles mouse events to select and manipulate keys.
    Ctrl + drag also moves the time cursor.
    """
    selectionChanged = Signal()

    def __init__(self, timer: Timer, editor: CurveEditor):
        super(CurveView, self).__init__(editor)
        self.__editor = editor
        self.__timer = timer
        if timer:
            timer.timeChanged.connect(self.__doRepaint)
        self.__undoStack = QUndoStack()
        self.__undoStack.indexChanged.connect(lambda x: self.update())
        self.__cameraUndoStack = QUndoStack()
        self.__cameraUndoStack.indexChanged.connect(lambda x: self.update())
        self.__models: Optional[tuple[QStandardItemModel, QItemSelectionModel]] = None
        self.__selection = Selection()
        self.__drag: Optional[Union[CameraZoomAction, CameraPanAction, DragAction, MarqueeSelectAction]] = None
        self.__camera: Optional[CurveViewCamera] = None
        self.__cache: Optional[Float4] = None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # TODO: use QPoint instead of list[int]
        self.__snap = [0, 0]
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.paintTime = 0

    def setSnapX(self, x: int) -> None:
        self.__snap[0] = max(0, x)

    # def setSnapY(self, y: int) -> None:
    #    self.__snap[1] = max(0, y)

    def selectedKeys(self) -> list[Key]:
        return self.__selection.keys()

    def undoStacks(self) -> tuple[QUndoStack, QUndoStack]:
        return self.__undoStack, self.__cameraUndoStack

    def __doRepaint(self, _) -> None:
        if self.__camera and self.__timer and self.__timer.isPlaying():
            rect = self.__camera.region()
            scaleX = self.width() / float(rect[2])
            x = (self.__localTime() - rect[0]) * scaleX
            self.update(int(x) - 10, 0, 20, self.height())
        else:
            self.update()

    # Frame our view on a set of keys
    def __frameOnKeys(self, keys: Iterable[Key]) -> None:
        boundsMin = None
        boundsMax = None

        for key in keys:
            point = key.point()
            if boundsMin is None:
                boundsMin = Vec2(point)
                boundsMax = Vec2(boundsMin)
                continue
            boundsMin.x = min(boundsMin.x, point.x)
            boundsMin.y = min(boundsMin.y, point.y)
            boundsMax.x = max(boundsMax.x, point.x)
            boundsMax.y = max(boundsMax.y, point.y)
        if boundsMin is None:
            return

        # Determine padding on both sides (32 pixels please)
        paddingX = (32.0 / max(1.0, self.width())) * (
            (boundsMax.x - boundsMin.x) if (boundsMax.x != boundsMin.x) else 1.0)
        paddingY = (32.0 / max(1.0, self.height())) * (
            (boundsMax.y - boundsMin.y) if (boundsMax.y != boundsMin.y) else 1.0)

        region = (boundsMin.x - paddingX,
                  boundsMin.y - paddingY,
                  boundsMax.x - boundsMin.x + 2 * paddingX,
                  boundsMax.y - boundsMin.y + 2 * paddingY)
        self.__cameraUndoStack.push(CameraFrameAction(self.__camera, region))
        self.update()

    # Frame our view on the selected keys (if any, otherwise on all)
    def frameSelected(self) -> None:
        keys = self.__selection.keys()
        if keys:
            self.__frameOnKeys(keys)
        else:
            self.frameAll()

    # Frame our view on all keys
    def frameAll(self) -> None:
        keys = []
        for row, i, key in self.iterVisibleKeys():
            keys.append(key)
        self.__frameOnKeys(keys)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_F:
            self.frameSelected()
            return
        if event.key() == Qt.Key.Key_A:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier == Qt.KeyboardModifier.ControlModifier:
                self.__editor.selectAllChannels()
            else:
                self.frameAll()
            return
        if event.key() == Qt.Key.Key_I:
            self.insertKey()
            return
        if event.key() == Qt.Key.Key_Delete:
            self.deleteKey()
            return
        super(CurveView, self).keyPressEvent(event)

    def __localTime(self) -> float:
        """Get time based on active shot.

        This allows curve editor and timer to sync their times
        even though the curve editor shows time local to the shot.
        """
        if not self.__timer:
            return 0.0
        shot = self.__editor.shot()
        if not shot:
            return self.__timer.time
        return (self.__timer.time - shot.start) * shot.speed - shot.preroll

    def __setLocalTime(self, t: float) -> None:
        """Set time based on active shot.

        This allows curve editor and timer to sync their times
        even though the curve editor shows time local to the shot.
        """
        if not self.__timer:
            return
        shot = self.__editor.shot()
        if not shot:
            self.__timer.time = t
            return
        self.__timer.time = (t + shot.preroll) / shot.speed + shot.start

    def insertKey(self) -> None:
        """Insert new key at current time, evaluates current animation to derive value."""
        curve = [self.__models[0].item(row).data() for row in self.visibleRows()]

        t = self.__localTime()
        if self.__snap[0]:
            t = round(t * self.__snap[0]) / self.__snap[0]
        self.__undoStack.push(InsertKeyAction(t, curve))

        self.update()

    def setKey(self, channels: Iterable[str], values: tuple[float]) -> None:
        curves = []
        for channel in channels:
            curves.append(self.__models[0].findItems(channel)[0].data())
        assert len(curves) == len(values)

        t = self.__localTime()
        if self.__snap[0]:
            t = round(t * self.__snap[0]) / self.__snap[0]
        self.__undoStack.push(SetKeyAction(t, curves, values))

        self.update()

    def onDuplicateKeys(self) -> None:
        keys = self.__selection.keys()
        # curve = [self.__models[0].item(row).data() for row in self.visibleRows()]
        # eys = self.__view.selectedKeys()
        # if not curve or not curve.keys:
        if not keys:
            return

        sourceFirstKeyTime = keys[0].time()
        for key in keys:
            sourceFirstKeyTime = min(sourceFirstKeyTime, key.time())

        newFirstKeyTime = self.__localTime()

        if self.__snap[0]:
            newFirstKeyTime = round(newFirstKeyTime * self.__snap[0]) / self.__snap[0]

        deltaTime = newFirstKeyTime - sourceFirstKeyTime

        for key in keys:
            action = SetKeyAction(key.time() + deltaTime, (key.parentCurve(),), (key.value(),))
            self.__undoStack.push(action)

        self.update()

    def deleteKey(self) -> None:
        selection = self.__selection.keys()
        if not selection:
            return
        self.__selection.clear()
        self.__undoStack.push(DeleteAction(selection))
        self.selectionChanged.emit()
        self.update()

    def sceneToPixelDistance(self, point: QPointF, overrideRegion: Optional[Float4] = None) -> QPoint:
        if not overrideRegion:
            w, h = self.__camera.region()[2:]
        else:
            w, h = overrideRegion[2:]
        return QPoint(int(point.x() * self.width() / w), int(point.y() * self.height() / h))

    def pixelToSceneDistance(self, point: QPoint, overrideRegion: Optional[Float4] = None) -> QPointF:
        if not overrideRegion:
            w, h = self.__camera.region()[2:]
        else:
            w, h = overrideRegion[2:]
        px = point.x() / self.width()
        py = point.y() / self.height()
        return QPointF(px * w, py * h)

    def sceneToPixel(self, point: QPointF, overrideRegion: Optional[Float4] = None) -> QPoint:
        if not overrideRegion:
            x, y, w, h = self.__camera.region()
        else:
            x, y, w, h = overrideRegion
        return QPoint(int((point.x() - x) * self.width() / w), int((point.y() - y) * self.height() / h))

    def pixelToScene(self, point: QPoint, overrideRegion: Optional[Float4] = None) -> QPointF:
        if not overrideRegion:
            x, y, w, h = self.__camera.region()
        else:
            x, y, w, h = overrideRegion
        px = point.x() / self.width()
        py = point.y() / self.height()
        return QPointF(x + px * w, y + py * h)

    def showEvent(self, event: QShowEvent) -> None:
        if self.__camera is None:
            self.__camera = CurveViewCamera(0.0, 0.0, 1.0, 1.0)
            self.__camera.regionChanged.connect(self.update)

    def createUndoView(self) -> QUndoView:
        view = QUndoView()
        view.setStack(self.__undoStack)
        return view

    def createCameraUndoView(self) -> QUndoView:
        view = QUndoView()
        view.setStack(self.__cameraUndoStack)
        return view

    def visibleRows(self) -> Iterable[int]:
        assert self.__models
        # 'cast' because there is a typing bug with tuple indexing here
        selectionModel = cast(QItemSelectionModel, self.__models[1])
        for idx in selectionModel.selectedRows():
            yield idx.row()

    def iterVisibleKeys(self) -> Iterable[tuple[int, int, Key]]:
        rows = self.visibleRows()
        for row in reversed(tuple(rows)):
            curve = self.__models[0].item(row).data()
            for i in range(len(curve) - 1, -1, -1):
                key = curve[i]
                yield row, i, key

    def deselectAll(self) -> None:
        # deselect all
        self.__selection.clear()
        self.selectionChanged.emit()

    def select(self, row: int, index: int, shift: bool, ctrl: bool) -> bool:
        state = self.__selection.isKeySelected(row, index)

        desiredState = shift == ctrl
        if shift and not ctrl:
            desiredState = not state

        if not shift and not ctrl:
            self.__selection.clear()
            self.__selection.addKey(row, index)
            self.selectionChanged.emit()
            return True

        if state != desiredState:
            if desiredState:
                self.__selection.addKey(row, index)
                self.selectionChanged.emit()
            else:
                self.__selection.deleteKey(row, index)
                self.selectionChanged.emit()
            return True
        return False

    def mousePressEvent(self, inEvent: QMouseEvent) -> None:
        self.__cache = self.__camera.region()
        event = RemappedEvent(self.pixelToScene(inEvent.pos(), self.__cache), inEvent)

        rows = tuple(self.visibleRows())

        if event.modifiers() & Qt.KeyboardModifier.AltModifier == Qt.KeyboardModifier.AltModifier:
            # edit camera action
            if event.button() == Qt.MouseButton.RightButton:
                # zoom
                self.__drag = CameraZoomAction(event, self.size(), self.__camera)
            else:
                # pan
                self.__drag = CameraPanAction(event, self.__camera)
            return

        if event.modifiers() & Qt.KeyboardModifier.ControlModifier == Qt.KeyboardModifier.ControlModifier:
            # set current time action
            self.__setLocalTime(event.x())
            self.update()
            return

        scale = self.width() / self.__cache[2], self.height() / self.__cache[3]

        if event.button() == Qt.MouseButton.MiddleButton:
            # begin drag action immediately
            selection = list(self.__selection.keys())
            if not selection:
                return
            self.__drag = DragAction(event, selection, None, scale, cast(tuple[int, int], tuple(self.__snap)))
            return

        TOLERANCE = 12
        x = event.x()
        y = event.y()

        # find point
        select = None
        for row in reversed(rows):
            curve = self.__models[0].item(row).data()
            for i in range(len(curve) - 1, -1, -1):
                key = curve[i]
                point = key.point()
                px = (abs(point.x - x) / self.__cache[2]) * self.width()
                py = (abs(point.y - y) / self.__cache[3]) * self.height()
                if px + py < TOLERANCE:
                    select = row, i
                    break

        # return if no point under mouse
        # TODO: we should do a marquee select if the target is not selected yet
        if not select:
            self.__drag = MarqueeSelectAction(event, self)
            return

        # begin drag action
        selectAction = functools.partial(self.select, select[0], select[1],
                                         event.modifiers() & Qt.KeyboardModifier.ShiftModifier == Qt.KeyboardModifier.ShiftModifier,
                                         event.modifiers() & Qt.KeyboardModifier.ControlModifier == Qt.KeyboardModifier.ControlModifier)
        selection = list(self.__selection.keys())
        self.__drag = DragAction(event, selection, selectAction, scale, cast(tuple[int, int], tuple(self.__snap)))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        event = RemappedEvent(self.pixelToScene(event.pos(), self.__cache), event)
        self.__cache = None

        # return if no drag action
        if not self.__drag:
            return

        # validate drag action
        if self.__drag.finalize(event):
            if isinstance(self.__drag, CameraUndoCommand):
                self.__cameraUndoStack.push(self.__drag)
            elif isinstance(self.__drag, QUndoCommand):
                self.__undoStack.push(self.__drag)
        self.__drag = None
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        event = RemappedEvent(self.pixelToScene(event.pos(), self.__cache), event)

        # return if no drag action
        if not self.__drag:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier == Qt.KeyboardModifier.ControlModifier:
                # set current time action
                self.__setLocalTime(event.x())
                self.update()
            return

        # drag should be implicit, so we can just validate and redraw the new state (moved or undone)
        self.__drag.update(event)
        self.update()

    def setModel(self, model: QStandardItemModel, selectionModel: QItemSelectionModel) -> None:
        self.__models = model, selectionModel
        self.__selection.setModel(model)

    def _drawBg(self, painter: QPainter, scaleX: float, scaleY: float, rect: Float4):
        backColor = QColor.fromRgb(96, 96, 96)
        linesColor = QColor.fromRgb(83, 83, 83)
        axisColor = QColor.fromRgb(122, 122, 122)

        # draw background
        painter.fillRect(0, 0, self.width(), self.height(), backColor)

        # draw grid and axes
        painter.save()
        painter.setPen(Qt.GlobalColor.black)

        # draw vertical lines (positive ones first, then negative ones)
        sx = 150.0 / scaleX
        sx = 5.0 ** round(log10(sx) - log10(5.5) + 0.5)
        x = (floor(rect[0] / sx) - 1) * sx
        while x < rect[0] + rect[2] + sx:
            x += sx
            px = self.sceneToPixel(QPointF(x, 0.0)).x()

            painter.setPen(Qt.GlobalColor.black)
            painter.drawText(px + 3.0, self.height() - 5.0, str(round(x, 4)))

            painter.setPen(axisColor if x == 0 else linesColor)
            painter.drawLine(px, 0, px, self.height())

        # draw horizontal lines (positive ones first, then negative ones)
        sy = 80.0 / scaleY
        sy = 5.0 ** round(log10(sy) - log10(5.5) + 0.5)
        y = (floor(rect[1] / sy) - 1) * sy
        while y < rect[1] + rect[3] + sy:
            y += sy
            py = self.sceneToPixel(QPointF(0.0, y)).y()

            painter.setPen(Qt.GlobalColor.black)
            painter.drawText(0 + 3.0, py - 1.0, str(round(y, 4)))

            painter.setPen(axisColor if y == 0 else linesColor)
            painter.drawLine(0, py, self.width(), py)

        painter.restore()

    def _drawCursor(self, painter: QPainter):
        # draw time cursor
        x = self.sceneToPixel(QPointF(self.__localTime(), 0.0)).x()
        painter.setPen(Qt.GlobalColor.red)
        painter.drawLine(QPoint(x, 2), QPoint(x, self.height()))
        markerTop = icons.getImage('TimeMarkerTop-24')
        painter.drawPixmap(QPoint(x - 4, 2), markerTop)

    def _drawFocus(self, painter: QPainter):
        if not self.hasFocus():
            return
        # outer border
        painter.setPen(QPen(self.palette().highlight(), 2.0))
        painter.drawRect(1, 1, self.width() - 2, self.height() - 2)
        painter.setClipRect(2, 2, self.width() - 4, self.height() - 4)

    __COLORS = {'x': Qt.GlobalColor.red, 'y': Qt.GlobalColor.green, 'z': Qt.GlobalColor.blue, 'w': Qt.GlobalColor.white}

    def _drawCurves(self, painter: QPainter, rows: Iterable[int], start: float, end: float, precision: float):
        # draw lines
        for row in rows:
            item = self.__models[0].item(row)
            curve = item.data()
            if not len(curve):
                continue
            identifier = item.text()[-1]
            if identifier in self.__COLORS:
                painter.setPen(self.__COLORS[identifier])
            else:
                painter.setPen(Qt.GlobalColor.red)
            prevPx = None
            x = max(start, curve[0].time())
            while x < min(end, curve[-1].time()):
                y = curve.evaluate(x)
                px = self.sceneToPixel(QPointF(x, y))
                if prevPx is not None:
                    painter.drawLine(prevPx, px)
                prevPx = px
                x += precision

    def _drawTangent(self, painter: QPainter, keyPoint: QPoint, tangent: Vec2):
        tangentScale = Vec2(self.width() / self.__camera.region()[2], self.height() / self.__camera.region()[3])

        # We want to draw a line of 50 px in the tangent direction
        # But we need that direction to be skewed based on the viewport zoom
        # So first we convert the tangent in units to a tangent in pixels
        tangent *= tangentScale
        # And THEN we get the direction
        tangent.normalize()

        tangentPoint = QPoint(int(keyPoint.x() + tangent.x * 50), int(keyPoint.y() + tangent.y * 50))
        painter.fillRect(QRect(tangentPoint.x() - 2, tangentPoint.y() - 2, 5, 5), Qt.GlobalColor.magenta)
        painter.setPen(Qt.GlobalColor.magenta)
        painter.drawLine(keyPoint, tangentPoint)

    def _drawKeys(self, painter: QPainter, rows: Iterable[int]) -> None:
        # draw points
        for row in rows:
            curve = self.__models[0].item(row).data()
            for i, key in enumerate(curve):
                point = self.sceneToPixel(QPointF(key.time(), key.value()))
                if self.__selection.isKeySelected(row, i):
                    # We're currently selected! Draw our tangent points
                    inTangent = (Vec2(-1.0, 0.0) if key.inTangent.sqrLen() == 0 else -key.inTangent)
                    self._drawTangent(painter, point, inTangent)
                    isStep = key.outTangent.y == float('inf')
                    if not isStep:  # don't draw stapped tangents
                        outTangent = (Vec2(1.0, 0.0) if key.outTangent.sqrLen() == 0 else key.outTangent)
                        outTangent.normalize()
                        self._drawTangent(painter, point, outTangent)
                    color = Qt.GlobalColor.yellow
                else:
                    color = Qt.GlobalColor.black
                painter.fillRect(QRectF(point.x() - 2, point.y() - 2, 5, 5), color)

    def paintEvent(self, event: QPaintEvent) -> None:
        if self.paintTime == time.time():
            return
        if not self.__models or not self.__models[0]:
            return

        painter = QPainter(self)

        rect = self.__camera.region()
        if not rect[2] or not rect[3]:
            return

        # scaling from view space to screen space
        scaleX = self.width() / rect[2]
        scaleY = self.height() / rect[3]

        self._drawBg(painter, scaleX, scaleY, rect)
        self._drawCursor(painter)
        self._drawFocus(painter)

        start = self.pixelToScene(QPoint(event.rect().x(), event.rect().y())).x()
        end = self.pixelToScene(QPoint(event.rect().right(), event.rect().bottom())).x()
        PRECISION = 4
        x, y, w, h = self.__camera.region()
        precision = (PRECISION / self.width()) * w

        self._drawCurves(painter, self.visibleRows(), start, end, precision)
        self._drawKeys(painter, self.visibleRows())

        # draw marquee selection area
        if self.__drag and hasattr(self.__drag, 'paint'):
            self.__drag.paint(painter)

        self.paintTime = time.time()

    def onChannelsChanged(self, *_) -> None:
        self.deselectAll()
        self.update()


class TangentMode(QWidget):
    """Tool bar to change the tangent mode of the selected keys."""
    valueChanged = Signal(int)

    def __init__(self) -> None:
        super(TangentMode, self).__init__()

        self.setLayout(hlayout())
        iconNames = ['tangent-auto', 'tangent-spline', 'tangent-linear', 'tangent-flat', 'tangent-stepped']
        self.__buttons = []
        for i, ico in enumerate(iconNames):
            btn = QPushButton(icons.get(ico), '')
            btn.setIconSize(QSize(24, 24))
            self.layout().addWidget(btn)
            btn.setCheckable(True)
            btn.clicked.connect(functools.partial(self.__update, i))
            self.__buttons.append(btn)

        # remove this button until we can actually drag tangents
        # self.__broken = QPushButton(icons.get('tangent-broken'), '')
        # self.__broken.setIconSize(QSize(24, 24))
        # self.__broken.setCheckable(True)
        # self.layout().addWidget(self.__broken)
        # self.tangentBrokenChanged = self.__broken.clicked

    def updateDisplayForKeys(self, keys: Iterable[Key]) -> None:
        # we may opt for a tri-state checkbox or tool icon later on, for now ambiguous-state is just displayed as 'off'
        TRI_STATE = False

        mode = list(set([key.tangentMode for key in keys]))
        for i, btn in enumerate(self.__buttons):
            if len(mode) != 1:
                btn.setChecked(TRI_STATE)
                continue
            if i in mode:
                continue
            btn.setChecked(False)
        for i in mode[:-1]:
            self.__buttons[i].setChecked(True)

        # broken = list(set([key.tangentBroken for key in keys]))
        # if not broken:
        #    self.__broken.setChecked(False)
        # else:
        #    self.__broken.setChecked(broken[0] if len(broken) == 1 else TRI_STATE)

    def __update(self, index: int) -> None:
        for i, btn in enumerate(self.__buttons):
            btn.setChecked(i == index)
        self.valueChanged.emit(index)


class CurveEditor(QWidget):
    """
    Curve editor widget.
    Creates and connects all components related to selecting and editing channel animation curves and keys.
    """

    def __init__(self, timer: Optional[Timer] = None, parent: Optional[QWidget] = None):
        super(CurveEditor, self).__init__(parent)
        self.setWindowTitle('CurveEditor')
        self.setObjectName('CurveEditor')

        self.__model = QStandardItemModel()
        self.__shot: Optional[Shot] = None
        self.__timer = timer

        tools = hlayout(spacing=4)

        add = QPushButton(icons.get('Add Node-48'), '')
        add.setToolTip('Add channels')
        add.setStatusTip('Add channels')
        add.setIconSize(QSize(24, 24))
        add.clicked.connect(self._onAddChannel)
        tools.addWidget(add)

        delete = QPushButton(icons.get('Delete Node-48'), '')
        delete.setToolTip('Delete channels')
        delete.setStatusTip('Delete channels')
        delete.setIconSize(QSize(24, 24))
        delete.clicked.connect(self._onDeleteChannel)
        tools.addWidget(delete)

        # input fields to move keys around with exact numbers
        self.__relative = CheckBox()
        tools.addWidget(QLabel('Relative:'))
        tools.addWidget(self.__relative)
        self.__relative.setValue((Qt.CheckState.Unchecked, Qt.CheckState.Checked, Qt.CheckState.Checked)[int(gSettings.value('RelativeKeyInput', 0))])
        self.__relative.valueChanged.connect(functools.partial(gSettings.setValue, 'RelativeKeyInput'))

        self.__time = DoubleSpinBox()
        self.__time.setDecimals(4)
        tools.addWidget(QLabel('Time:'))
        tools.addWidget(self.__time)
        self.__time.setEnabled(False)
        self.__time.setFixedWidth(70)
        self.__time.editingFinished.connect(self.__onShiftSelectedKeyTimes)

        self.__value = DoubleSpinBox()
        self.__value.setDecimals(4)
        tools.addWidget(QLabel('Value:'))
        tools.addWidget(self.__value)
        self.__value.setEnabled(False)
        self.__value.setFixedWidth(70)
        self.__value.editingFinished.connect(self.__onShiftSelectedKeyValues)

        # when editing keys with the input fields I'm storing the initial reference poitn so all changes may be relative
        self.__unshiftedKeyValue = [0.0, 0.0]

        self.__snapping = EnumBox(['1/1', '1/2', '1/4', '1/8', '1/16', '1/32', '1/64'])
        tools.addWidget(QLabel('Beat snap:'))
        tools.addWidget(self.__snapping)
        self.__snapping.setValue(int(gSettings.value('KeySnapSetting', 3)))
        self.__snapping.valueChanged.connect(functools.partial(gSettings.setValue, 'KeySnapSetting'))
        self.__snapping.valueChanged.connect(self.__updateSnapping)

        self.__tangentMode = TangentMode()
        tools.addWidget(self.__tangentMode)
        self.__tangentMode.valueChanged.connect(self.__setSelectedKeyTangents)
        # self.__tangentMode.tangentBrokenChanged.connect(self.__toggleBreakSelectedKeyTangents)

        positionKey = QPushButton(icons.get('Move-48'), '', self)
        positionKey.setToolTip('Key camera position into selection')
        positionKey.setStatusTip('Key camera position into selection')
        positionKey.setShortcut(QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_I))
        tools.addWidget(positionKey)
        self.requestPositionKey = positionKey.clicked

        rotationKey = QPushButton(icons.get('3D Rotate-48'), '', self)
        rotationKey.setToolTip('Key camera rotation into selection')
        rotationKey.setStatusTip('Key camera rotation into selection')
        rotationKey.setShortcut(QKeySequence(Qt.Modifier.SHIFT | Qt.Key.Key_O))
        tools.addWidget(rotationKey)
        self.requestRotationKey = rotationKey.clicked

        dupe = QPushButton(icons.get('Duplicate-Keys-24'), '')
        dupe.setToolTip('Duplicate selected keys')
        dupe.setStatusTip('Duplicate selected keys')
        dupe.setIconSize(QSize(24, 24))
        dupe.clicked.connect(self.__onDuplicateSelectedKeys)
        tools.addWidget(dupe)

        tools.addStretch(1)

        self.__channels = QListView()
        self.__channels.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.__channels.setModel(self.__model)
        # can't rename channels
        self.__channels.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.__view = CurveView(timer, self)
        self.__view.setModel(self.__model, self.__channels.selectionModel())

        self.__time.editingFinished.connect(self.__view.update)
        self.__value.editingFinished.connect(self.__view.update)
        self.__updateSnapping(self.__snapping.value())

        def forwardFocus(_) -> None:
            self.__view.setFocus(Qt.FocusReason.MouseFocusReason)

        self.__channels.focusInEvent = forwardFocus
        self.__channels.selectionModel().selectionChanged.connect(self.__view.onChannelsChanged)
        self.__view.selectionChanged.connect(self.__onUpdateKeyEditor)

        widget = QSplitterState('CurveEditor/Channels', Qt.Orientation.Horizontal)
        widget.addWidget(self.__channels)
        widget.addWidget(self.__view)
        widget.setStretchFactor(1, 1)
        widget.addWidget(self.__view.createUndoView())
        widget.addWidget(self.__view.createCameraUndoView())
        widget.setSizes([128, 128, 0, 0])

        layout = vlayout()
        self.setLayout(layout)

        layout.addLayout(tools)
        layout.addWidget(widget)
        layout.setStretch(1, 1)

        self.setEnabled(False)

        self.__channels.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.__channels.customContextMenuRequested.connect(self.__channelContextMenu)
        self.__channelMenu = QMenu()
        self.__copyAction = self.__channelMenu.addAction('Copy selected channel(s)')
        self.__copyAction.triggered.connect(self.__copySelectedChannels)
        self.__pasteAction = self.__channelMenu.addAction('Paste channels')
        self.__pasteAction.triggered.connect(self.__pasteChannels)
        self.__pasteOverAction = self.__channelMenu.addAction('Paste into selected channel')
        self.__pasteOverAction.triggered.connect(self.__pasteSelectedChannel)
        self.__clipboard = []

    def __copySelectedChannels(self) -> None:
        self.__clipboard = []
        for idx in self.__channels.selectedIndexes():
            item = self.__model.itemFromIndex(idx)
            self.__clipboard.append((item.text(), item.data()))
        self.__view.undoStacks()[0].clear()
        self.setShot(self.__shot)

    def __pasteChannels(self) -> None:
        if QMessageBox.warning(self, 'Warning', 'This action is not undoable. Continue?',
                               QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel) != QMessageBox.StandardButton.Ok:
            return
        for name, curve in self.__clipboard:
            self.__shot.curves[name] = curve.clone()
        self.__view.undoStacks()[0].clear()
        self.setShot(self.__shot)

    def __pasteSelectedChannel(self) -> None:
        if QMessageBox.warning(self, 'Warning', 'This action is not undoable. Continue?',
                               QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel) != QMessageBox.StandardButton.Ok:
            return
        indexes = self.__channels.selectedIndexes()
        assert len(self.__clipboard) == 1, 'Something went wrong when pasting from one channel to another, as it found multiple sources'
        assert len(indexes) == 1, 'Something went wrong when pasting from one channel to another, as it found multiple targets'
        self.__shot.curves[self.__model.itemFromIndex(indexes[0]).text()] = self.__clipboard[0][1].clone()
        self.__view.undoStacks()[0].clear()
        self.setShot(self.__shot)

    def __channelContextMenu(self, pos: QPoint) -> None:
        self.__copyAction.setEnabled(bool(len(self.__channels.selectedIndexes())))
        self.__pasteAction.setEnabled(bool(self.__clipboard))
        self.__pasteOverAction.setEnabled(len(self.__clipboard) == 1 and len(self.__channels.selectedIndexes()) == 1)
        self.__channelMenu.popup(self.__channels.mapToGlobal(pos))

    def __setSelectedKeyTangents(self, state: int) -> None:
        keys = self.__view.selectedKeys()
        edit = EditKeyAction(keys, [state] * len(keys), EditKeyAction.MODE_TANGENT_TYPE)
        if not edit.isEmpty():
            self.undoStacks()[0].push(edit)

    def __toggleBreakSelectedKeyTangents(self, state: int) -> None:
        keys = self.__view.selectedKeys()
        edit = EditKeyAction(keys, [state] * len(keys), EditKeyAction.MODE_TANGENT_BROKEN)
        if not edit.isEmpty():
            self.undoStacks()[0].push(edit)

    def __onShiftSelectedKeyTimeOrValue(self, widget: DoubleSpinBox, isTime: bool = True) -> None:
        keys = self.__view.selectedKeys()
        if self.__relative.value():
            delta = widget.value()
            if not delta:
                return
            values = []
            for key in keys:
                values.append((key.time() if isTime else key.value()) + delta)
            widget.setValueSilent(0.0)
        else:
            values = [widget.value()] * len(keys)

        edit = EditKeyAction(keys, values, EditKeyAction.MODE_TIME if isTime else EditKeyAction.MODE_VALUE)
        if not edit.isEmpty():
            self.undoStacks()[0].push(edit)

    def __onShiftSelectedKeyTimes(self) -> None:
        self.__onShiftSelectedKeyTimeOrValue(self.__time, True)

    def __onShiftSelectedKeyValues(self) -> None:
        self.__onShiftSelectedKeyTimeOrValue(self.__value, False)

    def selectAllChannels(self) -> None:
        self.__channels.selectAll()

    def __updateSnapping(self, state: int) -> None:
        self.__view.setSnapX(2 ** state)

    def __onUpdateKeyEditor(self) -> None:
        keys = self.__view.selectedKeys()
        self.__tangentMode.updateDisplayForKeys(keys)
        if not keys:
            self.__time.setEnabled(False)
            self.__value.setEnabled(False)
            return
        self.__time.setEnabled(True)
        self.__value.setEnabled(True)
        self.__time.setValue(keys[0].time())
        self.__value.setValue(keys[0].value())
        self.__unshiftedKeyValue = [keys[0].time(), keys[0].value()]

    def __onDuplicateSelectedKeys(self) -> None:
        self.__view.onDuplicateKeys()

    def shot(self) -> Optional[Shot]:
        return self.__shot

    def setKey(self, channels: Iterable[str], values: tuple[float]) -> None:
        self.__view.setKey(channels, values)

    def setTransformKey(self, values: tuple[float]) -> None:
        model = self.__channels.model()
        names = []
        for idx in self.__channels.selectedIndexes():
            names.append(model.item(idx.row(), 0).text())
        if len(names) == 1:
            if '.' not in names[0] or names[0].rsplit('.', 1)[1] not in 'xyz':
                print('Could not key position into channel %s. Channel should end with .x, .y or .z' % names[0])
                return
            baseName = names[0].rsplit('.', 1)[0]
            attr = 'xyz'
            for i in range(3):
                # TODO: Trying to figure out what exception to catch exactly
                # try:
                self.__view.setKey(('%s.%s' % (baseName, attr[i]),), (values[i],))
                # except:
                #    pass
            return
        # filter valid channels (.x, .y, .z suffix only)
        for i in range(len(names) - 1, -1, -1):
            if '.' not in names[i]:
                names.pop(i)
            if names[i].rsplit('.', 1)[1] not in 'xyz':
                names.pop(i)
        if len({name.rsplit('.', 1)[0] for name in names}) != 1:
            print('Could not key position into channels %s. Multiple channels selected, ambiguous which one.' % names)
            return
        if len(names) not in (2, 3):
            print('Could not key position into channels %s. Only vec2 and vec3 is supported.' % names)
            return
        self.__view.setKey(names, values)

    def undoStacks(self) -> tuple[QUndoStack, QUndoStack]:
        return self.__view.undoStacks()

    def setShot(self, shot: Optional[Shot]) -> None:
        self.__shot = shot
        self.__model.clear()
        if shot is None:
            self.setEnabled(False)
            self.__view.update()
            return
        self.setEnabled(True)
        for name in shot.curves:
            item = QStandardItem(name)
            item.setData(shot.curves[name])
            item.setData((shot.speed, shot.preroll), Qt.ItemDataRole.UserRole + 2)
            self.__model.appendRow(item)
        self.__channels.selectAll()
        self.__view.frameAll()

    def _onDeleteChannel(self) -> None:
        rows = list(self.__view.visibleRows())
        rows.sort(key=lambda x: -x)  # sort reversed so we remove last first
        for row in rows:
            name = self.__model.item(row).text()
            self.__model.removeRow(row)
            del self.__shot.curves[name]

    def _onAddChannel(self) -> None:
        msg = 'Name with optional [xy], [xyz], [xyzw] suffix\ne.g. "uPosition[xyz]", "uSize[xy]".'
        res = QInputDialog.getText(self, 'Create channel', msg)
        if not res[1] or not res[0]:
            return
        pat = re.compile(r'^[a-zA-Z_0-9]+(\[x(?:y(?:zw?)?)?])?$')
        if not pat.match(res[0]):
            msg = 'Invalid name or channel pattern given. Please use only alphanumeric characters and undersores; ' \
                  'also use only these masks: [x], [xy], [xyz], [xyzw].'
            QMessageBox.critical(self, 'Could not add attribute', msg)
            return
        if '[' not in res[0]:
            channelNames = [res[0]]
        else:
            channelNames = []
            attr, channels = res[0].split('[', 1)
            channels, remainder = channels.split(']')
            for channel in channels:
                channelNames.append('%s.%s' % (attr, channel))

        for channelName in channelNames:
            if self.__model.findItems(channelName):
                msg = 'An attribute with name "%s" already exists.\nNo attributes were added.' % channelName
                QMessageBox.critical(self, 'Could not add attribute', msg)
                return
        for channelName in channelNames:
            curve = Curve()
            self.__shot.curves[channelName] = curve
            item = QStandardItem(channelName)
            item.setData(curve)
            self.__model.appendRow(item)
