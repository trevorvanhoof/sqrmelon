from experiment.actions import KeySelectionEdit, RecursiveCommandError, MarqueeAction
from experiment.delegates import UndoableSelectionView, NamedColums
from experiment.keyselection import KeySelection
from experiment.model import Shot, Clip, Event
from qtutil import *


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



class CurveView(QWidget):
    # TODO: Curve loop mode change should trigger a repaint
    # TODO: Ability to watch shots instead of clips so shot loop mode and time range can be rendered as well (possibly just have an optional shot field that the painter picks up on)
    def __init__(self, source, undoStack, parent=None):
        super(CurveView, self).__init__(parent)
        self._source = source
        source.selectionChange.connect(self._pull)

        self._visibleCurves = set()
        self.setFocusPolicy(Qt.StrongFocus)
        self._selectionModel = KeySelection()
        self._selectionModel.changed.connect(self.repaint)
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
                if key in self._selectionModel:
                    keyStateChange[key] = 0

        # no keys to deselect
        if not keyStateChange:
            self.repaint()
            return

        try:
            cmd = KeySelectionEdit(self._selectionModel, keyStateChange)
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

    def _tangentEndPoint(self, src, dst, wt):
        TANGENT_LENGTH = 20.0
        x0, y0 = self.uToPx(src.x, src.y)
        x1, y1 = self.uToPx(dst.x, dst.y)
        dx = x1 - x0
        dy = abs(y1 - y0) * wt
        f = TANGENT_LENGTH / ((dx * dx + dy * dy) ** 0.5)
        x1, y1 = x0 + dx * f, y0 + dy * f
        return x1, y1

    def _drawTangent(self, painter, isSelected, src, dst, wt):
        # selection
        if isSelected:
            painter.setPen(Qt.white)
        else:
            painter.setPen(Qt.magenta)

        x0, y0 = self.uToPx(src.x, src.y)
        x1, y1 = self._tangentEndPoint(src, dst, wt)
        painter.drawLine(x0, y0, x1, y1)
        painter.drawRect(x1 - 1, y1 - 1, 2, 2)

    def itemsAt(self, x, y, w, h):
        for curve in self._visibleCurves:
            for i, key in enumerate(curve.keys):
                kx, ky = self.uToPx(key.x, key.y)
                if x <= kx <= x + w and y < ky <= y + h:
                    yield key, 1

                if key not in self._selectionModel:
                    # key or tangent must be selected for tangents to be visible
                    continue

                # in tangent
                if i > 0:
                    kx, ky = self._tangentEndPoint(key, curve.keys[i - 1], key.inTangentY)
                    if x <= kx <= x + w and y < ky <= y + h:
                        yield key, 1 << 1

                # out tangent
                if i < len(curve.keys) - 1:
                    kx, ky = self._tangentEndPoint(key, curve.keys[i + 1], -key.outTangentY)
                    if x <= kx <= x + w and y < ky <= y + h:
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
                selectionState = self._selectionModel.get(key, 0)

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
                    self._drawTangent(painter, selectionState & (1 << 1), key, curve.keys[i - 1], key.inTangentY)

                # out tangent
                if i < len(curve.keys) - 1:
                    self._drawTangent(painter, selectionState & (1 << 2), key, curve.keys[i + 1], -key.outTangentY)

        if self.action is not None:
            self.action.draw(painter)

    def mousePressEvent(self, event):
        self.action = MarqueeAction(self, self._selectionModel)
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