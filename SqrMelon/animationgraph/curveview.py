# TODO: scroll wheel zoom, zoom X and Y equally
from pycompat import *

from qtutil import *

import time
import icons
import functools
import re
from math import log10

from util import gSettings
from mathutil import Vec2

from animationgraph.curvedata import Curve
from animationgraph.curveselection import Selection, MarqueeSelectAction
from animationgraph.curveactions import InsertKeyAction, SetKeyAction, DeleteAction, DragAction, EditKeyAction
from animationgraph.viewactions import CameraFrameAction, CameraPanAction, CameraZoomAction, CameraUndoCommand


class CurveViewCamera(object):
    """
    Camera used by the CurveView renderer & interaction
    """

    def __init__(self, x, y, w, h):
        self.regionChanged = Signal()
        self.__visibleRegion = [x, y, w, h]

    def position(self):
        return self.__visibleRegion[0], self.__visibleRegion[1]

    def setPosition(self, x, y):
        self.__visibleRegion[:2] = x, y
        self.regionChanged.emit()

    def region(self):
        return tuple(self.__visibleRegion)

    def setRegion(self, x, y, w, h):
        self.__visibleRegion = [x, y, w, h]
        self.regionChanged.emit()


class RemappedEvent(object):
    """
    Utility to store event data in camera-space instead of pixel-space
    """

    def __init__(self, pos, event):
        self.__pos = pos
        self.__event = event

    def pos(self):
        return self.__pos

    def x(self):
        return self.__pos.x()

    def y(self):
        return self.__pos.y()

    def __getattr__(self, attr):
        return getattr(self.__event, attr)


class CurveView(QWidget):
    """
    Graph editor.
    Renders curves & handles mouse events to select and manipulate keys.
    Ctrl + drag also moves the time cursor.
    """
    selectionChanged = pyqtSignal()

    def __init__(self, timer, editor, parent=None):
        super(CurveView, self).__init__(parent)
        self.__editor = editor
        self.__timer = timer
        if timer:
            timer.timeChanged.connect(self.__doRepaint)
        self.__undoStack = QUndoStack()
        self.__undoStack.indexChanged.connect(lambda x: self.repaint())
        self.__cameraUndoStack = QUndoStack()
        self.__cameraUndoStack.indexChanged.connect(lambda x: self.repaint())
        self.__models = None
        self.__selection = Selection()
        self.__drag = None
        self.__camera = None
        self.__cache = None
        self.setFocusPolicy(Qt.StrongFocus)
        self.__snap = [0.0, 0.0]
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.paintTime = 0

    def setSnapX(self, x):
        self.__snap[0] = max(0.0, x)

    # def setSnapY(self, y):
    #    self.__snap[1] = max(0.0, y)

    def selectedKeys(self):
        return self.__selection.keys()

    def undoStacks(self):
        return self.__undoStack, self.__cameraUndoStack

    def __doRepaint(self, _):
        if self.__camera and self.__timer and self.__timer.isPlaying():
            rect = self.__camera.region()
            scaleX = self.width() / float(rect[2])
            x = (self.__localTime() - rect[0]) * scaleX
            self.repaint(x - 10, 0, 20, self.height())
        else:
            self.repaint()

    # Frame our view on a set of keys
    def __frameOnKeys(self, keys):
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
        self.repaint()

    # Frame our view on the selected keys (if any, otherwise on all)
    def frameSelected(self):
        keys = self.__selection.keys()
        if keys:
            self.__frameOnKeys(keys)
        else:
            self.frameAll()

    # Frame our view on all keys
    def frameAll(self):
        keys = []
        for row, i, key in self.iterVisibleKeys():
            keys.append(key)
        self.__frameOnKeys(keys)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F:
            self.frameSelected()
            return
        if event.key() == Qt.Key_A:
            if event.modifiers() & Qt.ControlModifier == Qt.ControlModifier:
                self.__editor.selectAllChannels()
            else:
                self.frameAll()
            return
        if event.key() == Qt.Key_I:
            self.insertKey()
            return
        if event.key() == Qt.Key_Delete:
            self.deleteKey()
            return
        super(CurveView, self).keyPressEvent(event)

    def __localTime(self):
        if not self.__timer:
            return 0.0
        shot = self.__editor.shot()
        if not shot:
            return self.__timer.time
        return (self.__timer.time - shot.start) * shot.speed - shot.preroll

    def __setLocalTime(self, t):
        if not self.__timer:
            return
        shot = self.__editor.shot()
        if not shot:
            self.__timer.time = t
            return
        self.__timer.time = (t + shot.preroll) / shot.speed + shot.start

    def insertKey(self):
        curve = [self.__models[0].item(row).data() for row in self.visibleRows()]

        t = self.__localTime()
        if self.__snap[0]:
            t = round(t * self.__snap[0]) / float(self.__snap[0])
        self.__undoStack.push(InsertKeyAction(t, curve))

        self.repaint()

    def setKey(self, channels, values):
        curves = []
        for channel in channels:
            curves.append(self.__models[0].findItems(channel)[0].data())

        t = self.__localTime()
        if self.__snap[0]:
            t = round(t * self.__snap[0]) / float(self.__snap[0])
        self.__undoStack.push(SetKeyAction(t, curves, values))

        self.repaint()

    def onDuplicateKeys(self):
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
            newFirstKeyTime = round(newFirstKeyTime * self.__snap[0]) / float(self.__snap[0])

        deltaTime = newFirstKeyTime - sourceFirstKeyTime

        for key in keys:
            action = SetKeyAction(key.time() + deltaTime, [key.parentCurve()], [key.value()])
            self.__undoStack.push(action)

        self.repaint()

    def deleteKey(self):
        selection = self.__selection.keys()
        if not selection:
            return
        self.__selection.clear()
        self.__undoStack.push(DeleteAction(selection))
        self.selectionChanged.emit()
        self.repaint()

    def pixelToScene(self, point, overrideRegion=None):
        if not overrideRegion:
            x, y, w, h = self.__camera.region()
        else:
            x, y, w, h = overrideRegion
        px = point.x() / float(self.width())
        py = point.y() / float(self.height())
        return QPointF(x + px * w, y + py * h)

    def showEvent(self, event):
        if self.__camera is None:
            self.__camera = CurveViewCamera(0.0, 0.0, 1.0, 1.0)
            self.__camera.regionChanged.connect(self.repaint)

    def createUndoView(self):
        view = QUndoView()
        view.setStack(self.__undoStack)
        return view

    def createCameraUndoView(self):
        view = QUndoView()
        view.setStack(self.__cameraUndoStack)
        return view

    def visibleRows(self):
        if self.__models[1]:
            rows = []
            for idx in self.__models[1].selectedRows():
                rows.append(idx.row())
        else:
            rows = range(self.__models[0].rowCount())
        return rows

    def iterVisibleKeys(self):
        rows = self.visibleRows()
        for row in reversed(rows):
            curve = self.__models[0].item(row).data()
            for i in range(len(curve) - 1, -1, -1):
                point = curve[i]
                yield row, i, point

    def deselectAll(self):
        # deselect all
        self.__selection.clear()
        self.selectionChanged.emit()

    def select(self, row, index, shift, ctrl):
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

    def mousePressEvent(self, inEvent):
        self.__cache = self.__camera.region()
        event = RemappedEvent(self.pixelToScene(inEvent.pos(), self.__cache), inEvent)

        rows = self.visibleRows()

        if event.modifiers() & Qt.AltModifier == Qt.AltModifier:
            # edit camera action
            if event.button() == Qt.RightButton:
                # zoom
                self.__drag = CameraZoomAction(event, self.size(), self.__camera)
            else:
                # pan
                self.__drag = CameraPanAction(event, self.__camera)
            return

        if event.modifiers() & Qt.ControlModifier == Qt.ControlModifier:
            # set current time action
            self.__setLocalTime(event.x())
            self.repaint()
            return

        scale = self.width() / self.__cache[2], self.height() / self.__cache[3]

        if event.button() == Qt.MiddleButton:
            # begin drag action immediately
            selection = list(self.__selection.keys())
            if not selection:
                return
            self.__drag = DragAction(event, selection, None, scale, tuple(self.__snap))
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
                                         event.modifiers() & Qt.ShiftModifier == Qt.ShiftModifier,
                                         event.modifiers() & Qt.ControlModifier == Qt.ControlModifier)
        selection = list(self.__selection.keys())
        self.__drag = DragAction(event, selection, selectAction, scale, tuple(self.__snap))

    def mouseReleaseEvent(self, event):
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
        self.repaint()

    def mouseMoveEvent(self, event):
        event = RemappedEvent(self.pixelToScene(event.pos(), self.__cache), event)

        # return if no drag action
        if not self.__drag:
            if event.modifiers() & Qt.ControlModifier == Qt.ControlModifier:
                # set current time action
                self.__setLocalTime(event.x())
                self.repaint()
            return

        # drag should be implicit, so we can just validate and redraw the new state (moved or undone)
        self.__drag.update(event)
        self.repaint()

    def setModel(self, model, selectionModel):
        self.__models = model, selectionModel
        self.__selection.setModel(model)

    def mapTangentToScreen(self, key, isInTangent):
        # Calculate the tangent position on screen (as a PointF)
        point = key.point()

        cameraRect = self.__camera.region()
        screenSize = Vec2(float(self.width()), float(self.height()))
        viewPort = Vec2(cameraRect[2], cameraRect[3])

        delta = Vec2(-key.inTangent if isInTangent else key.outTangent)
        if delta.sqrLen() == 0:
            delta = Vec2(-1.0 if isInTangent else 1.0, 0.0)
        px = (delta * screenSize) / viewPort
        px.normalize()
        px *= 50.0
        delta = (px / screenSize) * viewPort

        return Vec2(point.x + delta.x, point.y + delta.y)

    def _drawBg(self, painter, scaleX, scaleY, rect):
        backColor = QColor.fromRgb(96, 96, 96)
        linesColor = QColor.fromRgb(83, 83, 83)
        axisColor = QColor.fromRgb(122, 122, 122)

        # draw background
        painter.fillRect(0, 0, self.width(), self.height(), backColor)

        # draw grid and axes
        painter.save()
        painter.setPen(Qt.black)
        painter.scale(scaleX, scaleY)
        painter.translate(-rect[0], -rect[1])
        painter.scale(1.0 / scaleX, 1.0 / scaleY)

        # draw vertical lines (positive ones first, then negative ones)
        sx = 150.0 / scaleX
        sx = 5.0 ** round(log10(sx) - log10(5.5) + 0.5)
        x = 0
        for direction in range(2):
            while ((direction == 0) and (x < int(rect[0]) + int(rect[2]) + 2 * sx)) or (
                    (direction == 1) and (x > int(rect[0]) - sx)):
                painter.setPen(Qt.black)
                painter.drawText(x * scaleX + 3.0, (rect[1] + rect[3]) * scaleY - 5.0, str(round(x, 4)))
                painter.setPen(axisColor if x == 0 else linesColor)
                painter.drawLine(x * scaleX, rect[1] * scaleY, x * scaleX, (rect[1] + rect[3]) * scaleY)
                x += sx if direction == 0 else -sx
            x = -sx  # restart on left side

        # draw horizontal lines (positive ones first, then negative ones)
        sy = 80.0 / scaleY
        sy = 5.0 ** round(log10(sy) - log10(5.5) + 0.5)
        y = 0
        for direction in range(2):
            while ((direction == 0) and (y < int(rect[1]) + int(rect[3]) + 2 * sy)) or (
                    (direction == 1) and (y > int(rect[1]) - sy)):
                painter.setPen(Qt.black)
                painter.drawText(rect[0] * scaleX + 3.0, y * scaleY - 1.0, str(round(y, 4)))
                painter.setPen(axisColor if y == 0 else linesColor)
                painter.drawLine(rect[0] * scaleX, y * scaleY, (rect[0] + rect[2]) * scaleX, y * scaleY)
                y += sy if direction == 0 else -sy
            y = -sy  # restart on top side

        painter.restore()

    def _drawCursor(self, painter, scaleX, _, rect):
        # draw time cursor
        x = (self.__localTime() - rect[0]) * scaleX
        painter.setPen(Qt.red)
        painter.drawLine(QPoint(x, 2), QPoint(x, self.height()))
        markerTop = icons.getImage('TimeMarkerTop-24')
        painter.drawPixmap(QPoint(x - 4.0, 2), markerTop)

    def _drawFocus(self, painter, _, __, ___):
        # outer border
        if self.hasFocus():
            painter.setPen(QPen(self.palette().highlight(), 2.0))
            painter.drawRect(1, 1, self.width() - 2, self.height() - 2)
            painter.setClipRect(2, 2, self.width() - 4, self.height() - 4)

    __COLORS = {'x': Qt.red, 'y': Qt.green, 'z': Qt.blue, 'w': Qt.white}

    def _drawCurves(self, painter, rows, start, end, precision):
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
                painter.setPen(Qt.red)
            px, py = None, None
            x = max(start, curve[0].time())
            while x < min(end, curve[-1].time()):
                y = curve.evaluate(x)
                if py is not None:
                    painter.drawLine(QPointF(px, py), QPointF(x, y))
                px = x
                py = y
                x += precision

    def _drawKeys(self, painter, scaleX, scaleY, rows):
        # draw points
        pointWidth = 5.0 / scaleX
        pointHeight = 5.0 / scaleY
        tangentWidth = pointWidth
        tangentHeight = pointHeight

        for row in rows:
            curve = self.__models[0].item(row).data()
            for i, key in enumerate(curve):
                point = key.point()
                if self.__selection.isKeySelected(row, i):
                    # We're currently selected! Draw our tangent points
                    pointInTangent = self.mapTangentToScreen(key, True)

                    isStep = key.outTangent.y == float('inf')
                    if isStep:  # stepped tangent, don't draw because it's hella slow and infinitely far up
                        pointOutTangent = None
                    else:
                        pointOutTangent = self.mapTangentToScreen(key, False)

                    painter.fillRect(
                        QRectF(pointInTangent.x - tangentWidth / 2.0, pointInTangent.y - tangentHeight / 2.0,
                               tangentWidth, tangentHeight), Qt.magenta)
                    if not isStep:
                        painter.fillRect(
                            QRectF(pointOutTangent.x - tangentWidth / 2.0, pointOutTangent.y - tangentHeight / 2.0,
                                   tangentWidth, tangentHeight), Qt.magenta)
                    painter.setPen(Qt.magenta)
                    painter.drawLine(QPointF(pointInTangent.x, pointInTangent.y), QPointF(point.x, point.y))
                    if not isStep:
                        painter.drawLine(QPointF(pointOutTangent.x, pointOutTangent.y), QPointF(point.x, point.y))

                    color = Qt.yellow
                else:
                    color = Qt.black

                painter.fillRect(
                    QRectF(point.x - pointWidth / 2.0, point.y - pointHeight / 2.0, pointWidth, pointHeight), color)

    def paintEvent(self, event):
        if self.paintTime == time.time():
            return
        if not self.__models or not self.__models[0]:
            return

        painter = QPainter(self)

        rect = list(self.__camera.region())
        if not rect[2] or not rect[3]:
            return

        # scaling from view space to screen space
        scaleX = self.width() / float(rect[2])
        scaleY = self.height() / float(rect[3])

        self._drawBg(painter, scaleX, scaleY, rect)
        self._drawCursor(painter, scaleX, scaleY, rect)
        self._drawFocus(painter, scaleX, scaleY, rect)

        painter.scale(scaleX, scaleY)
        painter.translate(-rect[0], -rect[1])

        rows = self.visibleRows()
        start = self.pixelToScene(QPoint(event.rect().x(), event.rect().y())).x()
        end = self.pixelToScene(QPoint(event.rect().right(), event.rect().bottom())).x()
        PRECISION = 4
        x, y, w, h = self.__camera.region()
        precision = (PRECISION / float(self.width())) * w

        self._drawCurves(painter, rows, start, end, precision)
        self._drawKeys(painter, scaleX, scaleY, rows)

        # draw marquee selection area
        if self.__drag and hasattr(self.__drag, 'paint'):
            self.__drag.paint(painter)

        self.paintTime = time.time()

    def onChannelsChanged(self, *_):
        self.deselectAll()
        self.repaint()


class TangentMode(QWidget):
    """
    Tool bar to change the tangent mode of the selected keys.
    """
    valueChanged = pyqtSignal(int)

    def __init__(self):
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

    def updateDisplayForKeys(self, keys):
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

    def __update(self, index):
        for i, btn in enumerate(self.__buttons):
            btn.setChecked(i == index)
        self.valueChanged.emit(index)


class CurveEditor(QWidget):
    """
    Curve editor widget.
    Creates and connects all components related to selecting and editing channel animation curves and keys.
    """

    def __init__(self, timer=None, parent=None):
        super(CurveEditor, self).__init__(parent)
        self.setWindowTitle('CurveEditor')
        self.setObjectName('CurveEditor')

        self.__model = QStandardItemModel()
        self.__shot = None
        self.__timer = timer

        tools = hlayout(spacing=4.0)

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
        self.__relative.setValue((Qt.Unchecked, Qt.Checked, Qt.Checked)[int(gSettings.value('RelativeKeyInput', 0))])
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
        positionKey.setShortcut(QKeySequence(Qt.SHIFT + Qt.Key_I))
        tools.addWidget(positionKey)
        self.requestPositionKey = positionKey.clicked

        rotationKey = QPushButton(icons.get('3D Rotate-48'), '', self)
        rotationKey.setToolTip('Key camera rotation into selection')
        rotationKey.setStatusTip('Key camera rotation into selection')
        rotationKey.setShortcut(QKeySequence(Qt.SHIFT + Qt.Key_O))
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
        self.__channels.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.__channels.setModel(self.__model)
        # can't rename channels
        self.__channels.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.__view = CurveView(timer, self)
        self.__view.setModel(self.__model, self.__channels.selectionModel())

        self.__time.editingFinished.connect(self.__view.repaint)
        self.__value.editingFinished.connect(self.__view.repaint)
        self.__updateSnapping(self.__snapping.value())

        def forwardFocus(_):
            self.__view.setFocus(Qt.MouseFocusReason)

        self.__channels.focusInEvent = forwardFocus
        self.__channels.selectionModel().selectionChanged.connect(self.__view.onChannelsChanged)
        self.__view.selectionChanged.connect(self.__onUpdateKeyEditor)

        widget = QSplitterState('CurveEditor/Channels', Qt.Horizontal)
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

        self.__channels.setContextMenuPolicy(Qt.CustomContextMenu)
        self.__channels.customContextMenuRequested.connect(self.__channelContextMenu)
        self.__channelMenu = QMenu()
        self.__copyAction = self.__channelMenu.addAction('Copy selected channel(s)')
        self.__copyAction.triggered.connect(self.__copySelectedChannels)
        self.__pasteAction = self.__channelMenu.addAction('Paste channels')
        self.__pasteAction.triggered.connect(self.__pasteChannels)
        self.__pasteOverAction = self.__channelMenu.addAction('Paste into selected channel')
        self.__pasteOverAction.triggered.connect(self.__pasteSelectedChannel)
        self.__clipboard = []

    def __copySelectedChannels(self):
        self.__clipboard = []
        for idx in self.__channels.selectedIndexes():
            item = self.__model.itemFromIndex(idx)
            self.__clipboard.append((item.text(), item.data()))
        self.__view.undoStacks()[0].clear()
        self.setShot(self.__shot)

    def __pasteChannels(self):
        if QMessageBox.warning(self, 'Warning', 'This action is not undoable. Continue?',
                               QMessageBox.Ok | QMessageBox.Cancel) != QMessageBox.Ok:
            return
        for name, curve in self.__clipboard:
            self.__shot.curves[name] = curve.clone()
        self.__view.undoStacks()[0].clear()
        self.setShot(self.__shot)

    def __pasteSelectedChannel(self):
        if QMessageBox.warning(self, 'Warning', 'This action is not undoable. Continue?',
                               QMessageBox.Ok | QMessageBox.Cancel) != QMessageBox.Ok:
            return
        indexes = self.__channels.selectedIndexes()
        assert len(
            self.__clipboard) == 1, 'Something went wrong when pasting from one channel to another, ' \
                                    'as it found multiple sources'
        assert len(
            indexes) == 1, 'Something went wrong when pasting from one channel to another, as it found multiple targets'
        self.__shot.curves[self.__model.itemFromIndex(indexes[0]).text()] = self.__clipboard[0][1].clone()
        self.__view.undoStacks()[0].clear()
        self.setShot(self.__shot)

    def __channelContextMenu(self, pos):
        self.__copyAction.setEnabled(bool(len(self.__channels.selectedIndexes())))
        self.__pasteAction.setEnabled(bool(self.__clipboard))
        self.__pasteOverAction.setEnabled(len(self.__clipboard) == 1 and len(self.__channels.selectedIndexes()) == 1)
        self.__channelMenu.popup(self.__channels.mapToGlobal(pos))

    def __setSelectedKeyTangents(self, state):
        keys = self.__view.selectedKeys()
        edit = EditKeyAction(keys, [state] * len(keys), EditKeyAction.MODE_TANGENT_TYPE)
        if not edit.isEmpty():
            self.undoStacks()[0].push(edit)

    def __toggleBreakSelectedKeyTangents(self, state):
        keys = self.__view.selectedKeys()
        edit = EditKeyAction(keys, [state] * len(keys), EditKeyAction.MODE_TANGENT_BROKEN)
        if not edit.isEmpty():
            self.undoStacks()[0].push(edit)

    def __onShiftSelectedKeyTimeOrValue(self, widget, isTime=True):
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

    def __onShiftSelectedKeyTimes(self):
        self.__onShiftSelectedKeyTimeOrValue(self.__time, True)

    def __onShiftSelectedKeyValues(self):
        self.__onShiftSelectedKeyTimeOrValue(self.__value, False)

    def selectAllChannels(self):
        self.__channels.selectAll()

    def __updateSnapping(self, state):
        self.__view.setSnapX(2 ** state)

    def __onUpdateKeyEditor(self):
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

    def __onDuplicateSelectedKeys(self):
        self.__view.onDuplicateKeys()

    def shot(self):
        return self.__shot

    def setKey(self, channels, values):
        self.__view.setKey(channels, values)

    def setTransformKey(self, values):
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
                self.__view.setKey(['%s.%s' % (baseName, attr[i])], [values[i]])
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

    def undoStacks(self):
        return self.__view.undoStacks()

    def setShot(self, shot):
        self.__shot = shot
        self.__model.clear()
        if shot is None:
            self.setEnabled(False)
            self.__view.repaint()
            return
        self.setEnabled(True)
        for name in shot.curves:
            item = QStandardItem(name)
            item.setData(shot.curves[name])
            item.setData((shot.speed, shot.preroll), Qt.UserRole + 2)
            self.__model.appendRow(item)
        self.__channels.selectAll()
        self.__view.frameAll()

    def _onDeleteChannel(self):
        rows = list(self.__view.visibleRows())
        rows.sort(key=lambda x: -x)  # sort reversed so we remove last first
        for row in rows:
            name = self.__model.item(row).text()
            self.__model.removeRow(row)
            del self.__shot.curves[name]

    def _onAddChannel(self):
        msg = 'Name with optional [xy], [xyz], [xyzw] suffix\ne.g. "uPosition[xyz]", "uSize[xy]".'
        res = QInputDialog.getText(self, 'Create channel', msg)
        if not res[1] or not res[0]:
            return
        pat = re.compile(r'^[a-zA-Z_0-9]+(\[[x][y]?[z]?[w]?])?$')
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
