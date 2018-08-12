import re
import functools
from math import cos, asin

import icons
from experiment.actions import KeySelectionEdit, RecursiveCommandError, MarqueeAction, MoveKeyAction, MoveTangentAction, KeyEdit, CurveModelEdit, MoveTimeAction, DeleteKeys, InsertKeys, ViewPanAction, zoom, ViewZoomAction
from experiment.curvemodel import HermiteCurve, HermiteKey
from experiment.delegates import UndoableSelectionView
from experiment.enums import ETangentMode, ELoopMode
from experiment.keyselection import KeySelection
from experiment.model import Shot, Clip, Event
from qtutil import *


def sign(x): return -1 if x < 0 else 1


class CurveList(UndoableSelectionView):
    def __init__(self, source, undoStack, parent=None):
        super(CurveList, self).__init__(undoStack, parent)
        self._source = source
        source.selectionChange.connect(self._pull)

    @staticmethod
    def columnNames():
        return HermiteCurve.properties()

    def _pull(self, *args):
        # get first selected container
        clip = None  # empty stub
        curves = None
        for container in self._source.selectionModel().selectedRows():
            clip = container.data(Qt.UserRole + 1)
            curves = clip.curves
            break
        if self.model() == curves:
            return
        if curves is None:
            self.clearSelection()
        self.setModel(curves)
        self._updateNames()
        self.selectAll()


def createToolButton(iconName, toolTip, parent):
    btn = QPushButton(icons.get(iconName), '')
    btn.setToolTip(toolTip)
    btn.setStatusTip(toolTip)
    parent.addWidget(btn)
    return btn


class CurveUI(QWidget):
    # TODO: Show which clip / shot is active somehow (window title?)
    def __init__(self, eventManager, clipManager, undoStack):
        super(CurveUI, self).__init__()
        self._undoStack = undoStack

        mainLayout = vlayout()
        self.setLayout(mainLayout)
        toolBar = hlayout()

        createToolButton('Add Node-48', 'Add channel', toolBar).clicked.connect(self.__addChannel)

        btn = createToolButton('Delete Node-48', 'Remove selected channels', toolBar)
        btn.clicked.connect(self.__deleteChannels)
        self._curveActions = [btn]

        self._relative = QCheckBox()
        self._time = QDoubleSpinBox()
        self._value = QDoubleSpinBox()

        toolBar.addWidget(QLabel('Relative:'))
        toolBar.addWidget(self._relative)
        toolBar.addWidget(QLabel('Time:'))
        toolBar.addWidget(self._time)
        toolBar.addWidget(QLabel('Value:'))
        toolBar.addWidget(self._value)

        self._time.editingFinished.connect(self.__timeChanged)
        self._value.editingFinished.connect(self.__valueChanged)

        self._keyActions = [self._time, self._value]

        btn = createToolButton('tangent-auto', 'Set selected tangents to Auto', toolBar)
        btn.clicked.connect(functools.partial(self.__setTangentMode, ETangentMode.Auto))
        self._keyActions.append(btn)
        btn = createToolButton('tangent-spline', 'Set selected tangents to Spline', toolBar)
        btn.clicked.connect(functools.partial(self.__setTangentMode, ETangentMode.Spline))
        self._keyActions.append(btn)
        btn = createToolButton('tangent-linear', 'Set selected tangents to Linear', toolBar)
        btn.clicked.connect(functools.partial(self.__setTangentMode, ETangentMode.Linear))
        self._keyActions.append(btn)
        btn = createToolButton('tangent-flat', 'Set selected tangents to Flat', toolBar)
        btn.clicked.connect(functools.partial(self.__setTangentMode, ETangentMode.Flat))
        self._keyActions.append(btn)
        btn = createToolButton('tangent-stepped', 'Set selected tangents to Stepped', toolBar)
        btn.clicked.connect(functools.partial(self.__setTangentMode, ETangentMode.Stepped))
        self._keyActions.append(btn)
        btn = createToolButton('tangent-broken', 'Set selected tangents to Custom', toolBar)
        btn.clicked.connect(functools.partial(self.__setTangentMode, ETangentMode.Custom))
        self._keyActions.append(btn)

        btn = createToolButton('Move-48', 'Key camera position into selected channels', toolBar)
        btn.clicked.connect(self.__copyCameraPosition)
        self._curveActions.append(btn)
        btn = createToolButton('3D Rotate-48', 'Key camera radians into selected channels', toolBar)
        btn.clicked.connect(self.__copyCameraAngles)
        self._curveActions.append(btn)

        btn = createToolButton('Duplicate-Keys-24', 'Duplicated selected keys', toolBar)
        btn.clicked.connect(self.__copyKeys)
        self._keyActions.append(btn)

        toolBar.addStretch(1)

        splitter = QSplitter(Qt.Horizontal)
        clipManager.selectionChange.connect(self.__activeClipChanged)
        self._clipManager = clipManager
        self._eventManager = eventManager

        self._curveList = CurveList(clipManager, undoStack)
        self._curveList.selectionChange.connect(self.__visibleCurvesChanged)

        self._curveView = CurveView(self._curveList, undoStack)
        self._curveView.requestAllCurvesVisible.connect(self._curveList.selectAll)
        self._curveView.selectionModel.changed.connect(self.__keySelectionChanged)

        def forwardFocus(event):
            self._curveView.setFocus(Qt.MouseFocusReason)

        self._curveList.focusInEvent = forwardFocus

        splitter.addWidget(self._curveList)
        splitter.addWidget(self._curveView)

        mainLayout.addLayout(toolBar)
        mainLayout.addWidget(splitter)
        mainLayout.setStretch(0, 0)
        mainLayout.setStretch(1, 1)

        self._toolBar = toolBar
        toolBar.setEnabled(False)

    def setEvent(self, event):
        self._curveView.setEvent(event)

    def __activeClipChanged(self):
        pyObj = None
        for container in self._clipManager.selectionModel().selectedRows():
            pyObj = container.data(Qt.UserRole + 1)
            break
        self._toolBar.setEnabled(bool(pyObj))
        pyObj2 = None
        for container in self._eventManager.selectionModel().selectedRows():
            pyObj2 = container.data(Qt.UserRole + 1)
            if pyObj2.clip != pyObj:
                pyObj2 = None
            else:
                break
        self._curveView.setEvent(pyObj2)

    def __visibleCurvesChanged(self):
        state = self._curveView.hasVisibleCurves()
        for action in self._curveActions:
            action.setEnabled(state)

    def __keySelectionChanged(self):
        # set value and time fields to match selection
        cache = None
        for key, mask in self._curveView.selectionModel.iteritems():
            if not mask & 1:
                continue
            if cache is None:
                cache = key
            else:
                break
        if not cache:
            for action in self._keyActions:
                action.setEnabled(False)
            return
        for action in self._keyActions:
            action.setEnabled(True)
        self._time.setValue(cache.x)
        self._value.setValue(cache.y)

    def __valueChanged(self, value):
        restore = {}
        for key, mask in self._curveView.selectionModel.iteritems():
            if not mask & 1:
                continue
            restore[key] = key.copyData()
            key.y = value
        self._undostack.push(KeyEdit(restore, self._curveView.repaint))

    def __timeChanged(self, value):
        restore = {}
        for key, mask in self._curveView.selectionModel.iteritems():
            if not mask & 1:
                continue
            restore[key] = key.copyData()
            key.x = value
        self._undostack.push(KeyEdit(restore, self._curveView.repaint))

    def __setTangentMode(self, tangentMode):
        restore = {}
        dirty = False
        for key, mask in self._curveView.selectionModel.iteritems():
            restore[key] = key.copyData()
            if mask & 2:
                key.inTangentMode = tangentMode
                dirty = True

            if mask & 4:
                key.outTangentMode = tangentMode
                dirty = True

            if mask == 1:
                key.inTangentMode = tangentMode
                key.outTangentMode = tangentMode
                dirty = True

            key.computeTangents()

        if not dirty:
            return

        self._undoStack.push(KeyEdit(restore, self._curveView.repaint))
        self.repaint()

    def __addChannel(self):
        res = QInputDialog.getText(self, 'Create channel',
                                   'Name with optional [xy], [xyz], [xyzw] suffix\n'
                                   'e.g. "uPosition[xyz]", "uSize[xy]".')
        if not res[1] or not res[0]:
            return
        pat = re.compile(r'^[a-zA-Z_0-9]+(\[[x][y]?[z]?[w]?\])?$')
        if not pat.match(res[0]):
            QMessageBox.critical(self, 'Could not add attribute',
                                 'Invalid name or channel pattern given. '
                                 'Please use only alphanumeric characters and undersores;'
                                 'also use only these masks: [x], [xy], [xyz], [xyzw].')
            return
        if '[' not in res[0]:
            channelNames = [res[0]]
        else:
            channelNames = []
            attr, channels = res[0].split('[', 1)
            channels, remainder = channels.split(']')
            for channel in channels:
                channelNames.append('%s.%s' % (attr, channel))

        mdl = self._curveList.model()
        for channelName in channelNames:
            if mdl.findItems(channelName):
                QMessageBox.critical(self, 'Could not add attribute',
                                     'An attribute with name "%s" already exists.\n'
                                     'No attributes were added.' % channelName)
                return

        newCurves = []
        for channelName in channelNames:
            newCurves.append(HermiteCurve(channelName, ELoopMode.Clamp, []))
        if not newCurves:
            return
        self._undoStack.push(CurveModelEdit(mdl, newCurves, []))

    def __deleteChannels(self):
        rows = []
        for index in self._curveList.selectionModel().selectedRows():
            rows.append(index.row())
        if not rows:
            return
        mdl = self._curveList.model()
        self._undoStack.push(CurveModelEdit(mdl, [], rows))

    def __copyCameraPosition(self):
        raise NotImplementedError()

    def __copyCameraAngles(self):
        raise NotImplementedError()

    def __copyKeys(self):
        raise NotImplementedError()


class CurveView(QWidget):
    # TODO: Cursor management
    requestAllCurvesVisible = pyqtSignal()

    def __init__(self, source, undoStack, parent=None):
        super(CurveView, self).__init__(parent)
        self._source = source
        source.selectionChange.connect(self._pull)

        self._visibleCurves = set()
        self.setFocusPolicy(Qt.StrongFocus)
        self.selectionModel = KeySelection()
        self.selectionModel.changed.connect(self.repaint)
        self._undoStack = undoStack
        self.action = None

        # camera
        self.left = -1.0
        self.right = 13.0
        self.top = 2.0
        self.bottom = -1.0

        # time
        self.__time = 0.0

        self._event = None

    def setEvent(self, event):
        self._event = event
        self.repaint()

    def hasVisibleCurves(self):
        return bool(self._visibleCurves)

    @property
    def time(self):
        return self.__time

    @time.setter
    def time(self, value):
        self.__time = value
        self.repaint()

    def _pull(self, *args):
        newState = {index.data(Qt.UserRole + 1) for index in self._source.selectionModel().selectedRows()}
        deselected = self._visibleCurves - newState
        self._visibleCurves = newState

        self._source.model().dataChanged.connect(self.repaint)

        # when curves are deselected, we must deselect their keys as well
        keyStateChange = {}
        for curve in deselected:
            for key in curve.keys:
                if key in self.selectionModel:
                    keyStateChange[key] = 0

        # no keys to deselect
        if not keyStateChange:
            self.repaint()
            return

        try:
            cmd = KeySelectionEdit(self.selectionModel, keyStateChange)
            if cmd.canPush:
                self._undoStack.push(cmd)
            else:
                cmd.redo()
        except RecursiveCommandError:
            pass

    # mapping functions
    def xToT(self, x):
        return (x / float(self.width())) * (self.right - self.left) + self.left

    def tToX(self, t):
        return ((t - self.left) / (self.right - self.left)) * self.width()

    def yToV(self, y):
        return (y / float(self.height())) * (self.bottom - self.top) + self.top

    def vToY(self, v):
        return ((v - self.top) / (self.bottom - self.top)) * self.height()

    def uToPx(self, t, v):
        return self.tToX(t), self.vToY(v)

    def pxToU(self, x, y):
        return self.xToT(x), self.yToV(y)

    def _tangentEndPoint2(self, curve, i, isOut):
        key = curve.key(i)
        if not isOut:
            dx = curve.key(i - 1).x - key.x
            wt = key.inTangentY
        else:
            dx = curve.key(i + 1).x - key.x
            wt = key.outTangentY

        TANGENT_LENGTH = 20.0
        if abs(wt) == float('infinity'):
            return TANGENT_LENGTH, 0.0

        t = dx
        dx, dy = self.uToPx(t + self.left, wt + self.top)
        a = (dx * dx + dy * dy)
        if a == 0.0:
            return (TANGENT_LENGTH, 0.0)
        f = TANGENT_LENGTH / (a ** 0.5)
        return dx * f, dy * f * (1 if isOut else -1)

    def _drawTangent2(self, painter, isSelected, xpx, ypx, curve, i, isOut):
        # selection
        if isSelected:
            painter.setPen(Qt.white)
        else:
            painter.setPen(Qt.magenta)

        dx, dy = self._tangentEndPoint2(curve, i, isOut)

        painter.drawLine(xpx, ypx, xpx + dx, ypx + dy)
        painter.drawRect(xpx + dx - 1, ypx + dy - 1, 2, 2)

    def itemsAt(self, x, y, w, h):
        for curve in self._visibleCurves:
            for i, key in enumerate(curve.keys):
                kx, ky = self.uToPx(key.x, key.y)
                if x <= kx <= x + w and y < ky <= y + h:
                    yield key, 1

                if key not in self.selectionModel:
                    # key or tangent must be selected for tangents to be visible
                    continue

                # in tangent
                if i > 0:
                    tx, ty = self._tangentEndPoint2(curve, i, False)
                    if x <= kx + tx <= x + w and y < ky + ty <= y + h:
                        yield key, 1 << 1

                # out tangent
                if i < curve.keyCount() - 1:
                    tx, ty = self._tangentEndPoint2(curve, i, True)
                    if x <= kx + tx <= x + w and y < ky + ty <= y + h:
                        yield key, 1 << 2

    def paintEvent(self, event):
        painter = QPainter(self)
        ppt = None

        painter.fillRect(QRect(0, 0, self.width(), self.height()), QColor(40, 40, 40, 255))

        # paint evaluated data
        for curve in self._visibleCurves:
            for x in xrange(0, self.width(), 4):
                t = self.xToT(x)
                y = self.vToY(curve.evaluate(t))
                pt = QPoint(x, y)
                if x:
                    painter.drawLine(ppt, pt)
                ppt = pt

        # paint key points
        for curve in self._visibleCurves:
            for i, key in enumerate(curve.keys):
                # if key is selected, paint tangents
                selectionState = self.selectionModel.get(key, 0)

                # key selected
                if selectionState & 1:
                    painter.setPen(Qt.yellow)
                else:
                    painter.setPen(Qt.black)

                # key
                x, y = self.uToPx(key.x, key.y)
                painter.drawRect(x - 2, y - 2, 4, 4)

                # tangents not visible
                if not selectionState:
                    continue

                # in tangent
                if i > 0:
                    self._drawTangent2(painter, selectionState & (1 << 1), x, y, curve, i, False)

                # out tangent
                if i < curve.keyCount() - 1:
                    self._drawTangent2(painter, selectionState & (1 << 2), x, y, curve, i, True)

        # paint loop range
        if self._event:
            if isinstance(self._event, Event):
                left = self.tToX(self._event.roll)
                right = self.tToX(self._event.roll + self._event.duration * self._event.speed)
            else:
                left = self.tToX(0.0)
                right = self.tToX(self._event.duration)

            painter.setOpacity(0.5)

            painter.fillRect(0, 0, left, self.height(), Qt.black)
            painter.fillRect(right + 2, 0, self.width() - right, self.height(), Qt.black)

            painter.setPen(QColor(33, 150, 243))
            painter.drawLine(left, 16, left, self.height())
            painter.drawLine(right, 16, right, self.height())

            painter.setPen(QColor(63, 81, 181))
            painter.drawLine(left + 1, 16, left + 1, self.height())
            painter.drawLine(right + 1, 16, right + 1, self.height())

            painter.drawPixmap(left, 0, icons.getImage('left'))
            painter.drawPixmap(right - 4, 0, icons.getImage('right'))

            painter.setOpacity(1.0)

        # paint playhead
        x = self.tToX(self.time)
        painter.setPen(Qt.red)
        painter.drawLine(x, 16, x, self.height())
        painter.setPen(Qt.darkRed)
        painter.drawLine(x + 1, 0, x + 1, self.height())
        painter.drawPixmap(x - 4, 0, icons.getImage('playhead'))

        if self.action is not None:
            self.action.draw(painter)

    def wheelEvent(self, event):
        # zoom
        cx, cy = self.pxToU(event.x(), event.y())
        d = event.delta()
        zoom((cx, cy), self, d, d, self.repaint)

    def mousePressEvent(self, event):
        # alt for camera manip
        if event.modifiers() & Qt.AltModifier:
            # pan
            if event.button() == Qt.RightButton:
                self.action = ViewZoomAction(self, self.pxToU)
            else:
                self.action = ViewPanAction(self, self.size())

        elif event.button() == Qt.RightButton:
            # right button moves the time slider
            self.action = MoveTimeAction(self.time, self.xToT, functools.partial(self.__setattr__, 'time'))

        elif event.button() == Qt.MiddleButton and self.selectionModel:
            # middle click drag moves selection automatically
            for mask in self.selectionModel.itervalues():
                if mask & 6:
                    # prefer moving tangents
                    self.action = MoveTangentAction(self.selectionModel, self.pxToU, self.repaint)
                    break
            else:
                # only keys selected
                self.action = MoveKeyAction(self.pxToU, self.selectionModel, self.repaint)

        else:
            # left click drag moves selection only when clicking a selected element
            for key, mask in self.itemsAt(event.x() - 5, event.y() - 5, 10, 10):
                if key not in self.selectionModel:
                    continue
                if not self.selectionModel[key] & mask:
                    continue
                if mask == 1:
                    self.action = MoveKeyAction(self.pxToU, self.selectionModel, self.repaint)
                    break
                else:
                    self.action = MoveTangentAction(self.selectionModel, self.pxToU, self.repaint)
                    break
            else:
                # else we start a new selection action
                self.action = MarqueeAction(self, self.selectionModel)

        if self.action.mousePressEvent(event):
            self.repaint()

    def mouseReleaseEvent(self, event):
        action = self.action
        self.action = None
        # make sure self.action is None before calling mouseReleaseEvent so that:
        # 1. when returning True we will clear any painting done by self.action during mousePress/-Move
        # 2. when a callback results in a repaint the above holds true
        if action and action.mouseReleaseEvent(self._undoStack):
            self.repaint()

    def mouseMoveEvent(self, event):
        if self.action:
            if self.action.mouseMoveEvent(event):
                self.repaint()

    def _frameKeys(self, keyGenerator):
        left = float('infinity')
        right = -float('infinity')
        top = float('infinity')
        bottom = -float('infinity')

        for key in keyGenerator:
            left = min(key.x, left)
            right = max(key.x, right)
            top = min(key.y, top)
            bottom = max(key.y, bottom)

        if left == float('infinity'):
            left, right = -0.1, 0.1
        if left == right:
            left -= 0.1
            right += 0.1

        if top == float('infinity'):
            top, bottom = -0.1, 0.1
        if top == bottom:
            top -= 0.1
            bottom += 0.1

        extents = (right - left) * 0.5, (bottom - top) * 0.5
        center = left + extents[0], top + extents[1]
        self.left = center[0] - extents[0] * 1.5
        self.right = center[0] + extents[0] * 1.5
        self.bottom = center[1] - extents[1] * 1.5
        self.top = center[1] + extents[1] * 1.5

    def frameAll(self):
        def generator():
            for curve in self._visibleCurves:
                for key in curve.keys:
                    yield key

        self._frameKeys(generator())

    def frameSelected(self):
        if self.selectionModel:
            self._frameKeys(self.selectionModel.__iter__())
        else:
            self.frameAll()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_A:
            if event.modifiers() == Qt.ControlModifier:
                self.requestAllCurvesVisible.emit()
                return
            # frame all
            self.frameAll()
            self.repaint()
        elif event.key() == Qt.Key_F:
            # frame selection (or all if none selected)
            self.frameSelected()
            self.repaint()
        elif event.key() == Qt.Key_I:
            # insert key if there's no key at this time
            apply = {}
            for curve in self._visibleCurves:
                apply[curve] = HermiteKey(self.time, curve.evaluate(self.time), 0, 0, ETangentMode.Auto, ETangentMode.Auto, curve)
            self._undoStack.push(InsertKeys(apply, self.repaint))
        elif event.key() == Qt.Key_Delete:
            # delete selected keys
            apply = {}
            for key, mask in self.selectionModel.iteritems():
                if mask & 1:
                    apply.setdefault(key.parent, []).append(key)
            self._undoStack.push(DeleteKeys(apply, self.repaint))


class ShotManager(UndoableSelectionView):
    def __init__(self, undoStack, parent=None):
        super(ShotManager, self).__init__(undoStack, parent)
        self.model().itemChanged.connect(self.__fwdItemChanged)

    def __fwdItemChanged(self, item):
        self.model().item(item.row()).data().propertyChanged(item.column())

    @staticmethod
    def columnNames():
        return Shot.properties()


class EventManager(UndoableSelectionView):
    def __init__(self, undoStack, parent=None):
        super(EventManager, self).__init__(undoStack, parent)
        self.model().itemChanged.connect(self.__fwdItemChanged)

    def __fwdItemChanged(self, item):
        self.model().item(item.row()).data().propertyChanged(item.column())

    @staticmethod
    def columnNames():
        return Event.properties()


class ClipManager(UndoableSelectionView):
    def __init__(self, source, undoStack, parent=None):
        super(ClipManager, self).__init__(undoStack, parent)
        self._source = source
        source.selectionChange.connect(self._pull)

    def _pull(self, *args):
        # get first selected container
        pyObj = None  # empty stub
        for container in self._source.selectionModel().selectedRows():
            pyObj = container.data(Qt.UserRole + 1)
            break
        if pyObj is None:
            return
        items = self.model().findItems(str(pyObj.clip))
        if items:
            index = self.model().indexFromItem(items[0])
            self.selectionModel().select(index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)

    @staticmethod
    def columnNames():
        return Clip.properties()
