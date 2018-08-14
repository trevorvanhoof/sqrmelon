import functools

import icons
from experiment.actions import KeySelectionEdit, RecursiveCommandError, MoveTimeAction, MoveTangentAction, MoveKeyAction, MarqueeAction, InsertKeys, DeleteKeys
from experiment.curvemodel import HermiteKey
from experiment.enums import ETangentMode
from experiment.gridview import GridView
from experiment.keyselection import KeySelection
from experiment.model import Event
from qtutil import *


class CurveView(GridView):
    # TODO: Cursor management
    # TODO: Timeline time cursor
    # TODO: Timeline editing
    # TODO: Curve view time should control timeline time when an event range is known
    requestAllCurvesVisible = pyqtSignal()

    def __init__(self, source, undoStack, parent=None):
        super(CurveView, self).__init__(parent)

        self._source = source
        source.selectionChange.connect(self._pull)

        self._visibleCurves = set()
        self.selectionModel = KeySelection()
        self.selectionModel.changed.connect(self.repaint)
        self._undoStack = undoStack

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
        dx, dy = self.uToPx(t + self._viewRect.left, wt + self._viewRect.top)
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
        super(CurveView, self).paintEvent(event)

        painter = QPainter(self)
        ppt = None

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

        if self._action is not None:
            self._action.draw(painter)

    def mousePressEvent(self, event):
        # alt for camera manip
        if event.modifiers() & Qt.AltModifier:
            super(CurveView, self).mousePressEvent(event)
            # creating self._action, calling it's mousePressEvent and repainting is handled in base class
            return

        elif event.button() == Qt.RightButton:
            # right button moves the time slider
            self.action = MoveTimeAction(self.time, self.xToT, functools.partial(self.__setattr__, 'time'), bool(self._event))

        elif event.button() == Qt.MiddleButton and self.selectionModel:
            # middle click drag moves selection automatically
            for mask in self.selectionModel.itervalues():
                if mask & 6:
                    # prefer moving tangents
                    self._action = MoveTangentAction(self.selectionModel, self.pxToU, self.repaint)
                    break
            else:
                # only keys selected
                self._action = MoveKeyAction(self.pxToU, self.selectionModel, self.repaint)

        else:
            # left click drag moves selection only when clicking a selected element
            for key, mask in self.itemsAt(event.x() - 5, event.y() - 5, 10, 10):
                if key not in self.selectionModel:
                    continue
                if not self.selectionModel[key] & mask:
                    continue
                if mask == 1:
                    self._action = MoveKeyAction(self.pxToU, self.selectionModel, self.repaint)
                    break
                else:
                    self._action = MoveTangentAction(self.selectionModel, self.pxToU, self.repaint)
                    break
            else:
                # else we start a new selection action
                self._action = MarqueeAction(self, self.selectionModel)

        if self._action.mousePressEvent(event):
            self.repaint()

    def mouseReleaseEvent(self, event):
        action = self._action
        super(CurveView, self).mouseReleaseEvent(event)  # self._action = None
        # make sure self.action is None before calling mouseReleaseEvent so that:
        # 1. when returning True we will clear any painting done by self.action during mousePress/-Move
        # 2. when a callback results in a repaint the above holds true
        if action and action.mouseReleaseEvent(self._undoStack):
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
        self._viewRect.left = center[0] - extents[0] * 1.5
        self._viewRect.right = center[0] + extents[0] * 1.5
        self._viewRect.bottom = center[1] - extents[1] * 1.5
        self._viewRect.top = center[1] + extents[1] * 1.5

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
