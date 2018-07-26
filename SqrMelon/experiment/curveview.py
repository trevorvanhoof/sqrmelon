from experiment.actions import MarqueeAction, KeySelectionEdit, SelectionModelEdit
from experiment.keyselection import KeySelection
from qtutil import *


class CurveView(QWidget):
    def __init__(self, undoStack, curves, parent=None):
        super(CurveView, self).__init__(parent)

        self.setFocusPolicy(Qt.StrongFocus)

        self.__selectionModel = KeySelection()
        self.__selectionModel.changed.connect(self.repaint)

        self.__undoStack = undoStack

        self.action = None

        self.left = -1.0
        self.right = 13.0

        self.top = 2.0
        self.bottom = -1.0

        self.__cache = curves

    def setVisibleCurvesCache(self, curves):
        self.__cache = curves
        self.repaint()

    def createDeselectCurvesCommand(self, deselectedIndexes, parent=None):
        # when curves are deselected, we must deselect their keys as well
        keyStateChange = {}
        for index in deselectedIndexes:
            curve = index.data(Qt.UserRole + 1)
            for key in curve.keys:
                if key in self.__selectionModel:
                    keyStateChange[key] = 0
        return KeySelectionEdit(self.__selectionModel, keyStateChange, parent)

    @property
    def selectionModel(self):
        return self.__selectionModel

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

    def __tangentEndPoint(self, src, dst, wt):
        TANGENT_LENGTH = 20.0
        x0, y0 = self.uToPx(src.x, src.y)
        x1, y1 = self.uToPx(dst.x, dst.y)
        dx = x1 - x0
        dy = abs(y1 - y0) * wt
        f = TANGENT_LENGTH / ((dx * dx + dy * dy) ** 0.5)
        x1, y1 = x0 + dx * f, y0 + dy * f
        return x1, y1

    def __drawTangent(self, painter, isSelected, src, dst, wt):
        # selection
        if isSelected:
            painter.setPen(Qt.white)
        else:
            painter.setPen(Qt.magenta)

        x0, y0 = self.uToPx(src.x, src.y)
        x1, y1 = self.__tangentEndPoint(src, dst, wt)
        painter.drawLine(x0, y0, x1, y1)
        painter.drawRect(x1 - 1, y1 - 1, 2, 2)

    def itemsAt(self, x, y, w, h):
        for curve in self.__cache:
            for i, key in enumerate(curve.keys):
                kx, ky = self.uToPx(key.x, key.y)
                if x <= kx <= x + w and y < ky <= y + h:
                    yield key, 1

                if key not in self.__selectionModel:
                    # key or tangent must be selected for tangents to be visible
                    continue

                # in tangent
                if i > 0:
                    kx, ky = self.__tangentEndPoint(key, curve.keys[i - 1], key.inTangentY)
                    if x <= kx <= x + w and y < ky <= y + h:
                        yield key, 1 << 1

                # out tangent
                if i < len(curve.keys) - 1:
                    kx, ky = self.__tangentEndPoint(key, curve.keys[i + 1], -key.outTangentY)
                    if x <= kx <= x + w and y < ky <= y + h:
                        yield key, 1 << 2

    def paintEvent(self, event):
        painter = QPainter(self)
        ppt = None

        painter.fillRect(QRect(0, 0, self.width(), self.height()), QColor(40, 40, 40, 255))

        # paint evaluated data
        for curve in self.__cache:
            for x in xrange(0, self.width(), 4):
                t = self.xToT(x)
                y = self.vToY(curve.evaluate(t))
                pt = QPoint(x, y)
                if x:
                    painter.drawLine(ppt, pt)
                ppt = pt

        # paint key points
        for curve in self.__cache:
            for i, key in enumerate(curve.keys):
                # if key is selected, paint tangents
                selectionState = self.__selectionModel.get(key, 0)

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
                    self.__drawTangent(painter, selectionState & (1 << 1), key, curve.keys[i - 1], key.inTangentY)

                # out tangent
                if i < len(curve.keys) - 1:
                    self.__drawTangent(painter, selectionState & (1 << 2), key, curve.keys[i + 1], -key.outTangentY)

        if self.action is not None:
            self.action.draw(painter)

    def mousePressEvent(self, event):
        self.action = MarqueeAction(self, self.__selectionModel)
        if self.action.mousePressEvent(event):
            self.repaint()

    def mouseReleaseEvent(self, event):
        action = self.action
        self.action = None
        # make sure self.action is None before calling mouseReleaseEvent so that:
        # 1. when returning True we will clear any painting done by self.action during mousePress/-Move
        # 2. when a callback results in a repaint the above holds true
        if action and action.mouseReleaseEvent(self.__undoStack):
            self.repaint()

    def mouseMoveEvent(self, event):
        if self.action:
            if self.action.mouseMoveEvent(event):
                self.repaint()


class CurveWidget(QSplitter):
    def __init__(self, undoStack, parent=None):
        super(CurveWidget, self).__init__(Qt.Horizontal, parent)
        self.__curveListView = QListView()
        self.addWidget(self.__curveListView)

        self.__curveListView.setModel(QStandardItemModel())
        self.__curveListView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.__curveListView.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.__curveListModel = self.__curveListView.model()

        # track clip curves dict so this widget can add/remove channels
        # TODO: clip.curves should be a QStandardItemModel as well, so we can directly view it
        # self.__underlyingData = None

        self.__visibleCurvesModel = self.__curveListView.selectionModel()
        self.__visibleCurvesModel.selectionChanged.connect(self.__visibleCurvesChanged)

        self.__view = CurveView(undoStack, self.__visibleCurves())
        self.__undoStack = undoStack
        self.addWidget(self.__view)


    def focusCurves(self, curvesDict):
        if not curvesDict:
            # clear curve selection
            self.__visibleCurvesModel.clearSelection()
            self.__curveListModel.clear()
            return

        self.__curveListModel.clear()
        for name, curve in curvesDict.iteritems():
            it = QStandardItem(name)
            it.setData(curve)
            self.__curveListModel.appendRow(it)

        self.__curveListView.selectAll()

    def __visibleCurves(self):
        return [index.data(Qt.UserRole + 1) for index in self.__visibleCurvesModel.selectedRows()]

    def __visibleCurvesChanged(self, selected, deselected):
        if deselected.indexes():
            # deselect the keys we can no longer see and
            # make that undoable, together with the curve hiding itself
            self.__undoStack.push(self.__view.createDeselectCurvesCommand(deselected.indexes()))

        self.__undoStack.push(SelectionModelEdit(self.__visibleCurvesModel, selected, deselected))

        self.__view.setVisibleCurvesCache(self.__visibleCurves())
