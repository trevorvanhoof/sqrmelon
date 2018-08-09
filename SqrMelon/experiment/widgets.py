import re
import functools
from math import cos, asin

import icons
from experiment.actions import KeySelectionEdit, RecursiveCommandError, MarqueeAction, MoveKeyAction, MoveTangentAction, KeyEdit
from experiment.curvemodel import HermiteCurve
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
        curves = None  # empty stub
        for container in self._source.selectionModel().selectedRows():
            curves = container.data(Qt.UserRole + 1).curves
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
    def __init__(self, clipManager, undoStack):
        super(CurveUI, self).__init__()
        mainLayout = QVBoxLayout()
        self.setLayout(mainLayout)
        toolBar = QHBoxLayout()

        createToolButton('Add Node-48', 'Add channel', toolBar).clicked.connect(self.__addChannel)
        createToolButton('Delete Node-48', 'Remove selected channels', toolBar).clicked.connect(self.__deleteChannels)

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

        createToolButton('tangent-auto', 'Set selected tangents to Auto', toolBar).clicked.connect(functools.partial(self.__setTangentMode, ETangentMode.Auto))
        createToolButton('tangent-spline', 'Set selected tangents to Spline', toolBar).clicked.connect(functools.partial(self.__setTangentMode, ETangentMode.Spline))
        createToolButton('tangent-linear', 'Set selected tangents to Linear', toolBar).clicked.connect(functools.partial(self.__setTangentMode, ETangentMode.Linear))
        createToolButton('tangent-flat', 'Set selected tangents to Flat', toolBar).clicked.connect(functools.partial(self.__setTangentMode, ETangentMode.Flat))
        createToolButton('tangent-stepped', 'Set selected tangents to Stepped', toolBar).clicked.connect(functools.partial(self.__setTangentMode, ETangentMode.Stepped))
        createToolButton('tangent-broken', 'Set selected tangents to Custom', toolBar).clicked.connect(functools.partial(self.__setTangentMode, ETangentMode.Custom))

        createToolButton('Move-48', 'Key camera position into selected channels', toolBar).clicked.connect(self.__copyCameraPosition)
        createToolButton('3D Rotate-48', 'Key camera radians into selected channels', toolBar).clicked.connect(self.__copyCameraAngles)
        createToolButton('Duplicate-Keys-24', 'Duplicated selected keys', toolBar).clicked.connect(self.__copyKeys)

        toolBar.addStretch(1)

        splitter = QSplitter(Qt.Horizontal)
        self._curveList = CurveList(clipManager, undoStack)
        self._curveView = CurveView(self._curveList, undoStack)
        self._undoStack = undoStack
        self._curveView.selectionModel.changed.connect(self.__keySelectionChanged)
        splitter.addWidget(self._curveList)
        splitter.addWidget(self._curveView)

        mainLayout.addLayout(toolBar)
        mainLayout.addWidget(splitter)
        mainLayout.setStretch(0, 0)
        mainLayout.setStretch(1, 1)

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
            self._time.setEnabled(False)
            self._value.setEnabled(False)
            return
        self._time.setEnabled(True)
        self._value.setEnabled(True)
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
        for key, mask in self._curveView.selectionModel.iteritems():
            restore[key] = key.copyData()
            if mask & 2:
                key.inTangentMode = tangentMode

            if mask & 4:
                key.outTangentMode = tangentMode

            if mask == 1:
                key.inTangentMode = tangentMode
                key.outTangentMode = tangentMode

            key.computeTangents()
        self._undoStack.push(KeyEdit(restore, self._curveView.repaint))

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

        for channelName in channelNames:
            mdl.appendRow(HermiteCurve(channelName, ELoopMode.Clamp, []).items)

    def __deleteChannels(self):
        pass

    def __copyCameraPosition(self):
        pass

    def __copyCameraAngles(self):
        pass

    def __copyKeys(self):
        pass


class CurveView(QWidget):
    # TODO: Curve loop mode change should trigger a repaint
    # TODO: Ability to watch shots instead of clips so shot loop mode and time range can be rendered as well (possibly just have an optional shot field that the painter picks up on)
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

    def _pull(self, *args):
        newState = {index.data(Qt.UserRole + 1) for index in self._source.selectionModel().selectedRows()}
        deselected = self._visibleCurves - newState
        self._visibleCurves = newState

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

        t = cos(asin(wt / 3.0)) * dx
        dx, dy = self.uToPx(t + self.left, wt + self.top)
        TANGENT_LENGTH = 20.0
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

        if self.action is not None:
            self.action.draw(painter)

    def mousePressEvent(self, event):
        # middle click drag moves selection automatically
        if event.button() == Qt.MiddleButton and self.selectionModel:
            for mask in self.selectionModel.itervalues():
                if mask & 6:
                    # prefer moving tangents
                    self.action = MoveTangentAction(self.selectionModel, self.pxToU, self.repaint)
                    break
            else:
                # only keys selected
                self.action = MoveKeyAction(self.selectionModel, self.pxToU, self.repaint)
        else:
            # left click drag moves selection only when clicking a selected element
            for key, mask in self.itemsAt(event.x() - 5, event.y() - 5, 10, 10):
                if key not in self.selectionModel:
                    continue
                if not self.selectionModel[key] & mask:
                    continue
                if mask == 1:
                    self.action = MoveKeyAction(self.selectionModel, self.pxToU, self.repaint)
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
