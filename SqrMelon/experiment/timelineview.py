import functools

from experiment.actions import MarqueeActionBase, MoveTimeAction, MoveEventAction
from experiment.gridview import GridView
from experiment.model import Shot
from experiment.timer import drawPlayhead
from qtutil import *
import icons


class GraphicsItemEvent(object):
    trackHeight = 24
    handleWidth = 8
    padding = (4, 4, 4, 4)
    iconSize = 16

    _ico = None

    @classmethod
    def iconName(cls):
        return 'Curves'

    def __init__(self, event, x, width):
        self.event = event
        self.rect = QRect(x,
                          event.track * GraphicsItemEvent.trackHeight,
                          width,
                          GraphicsItemEvent.trackHeight)
        self.iconRect = QRect(x, self.rect.y() + (self.rect.height() - GraphicsItemShot.iconSize) / 2, GraphicsItemShot.iconSize, GraphicsItemShot.iconSize)
        self.textRect = self.rect.adjusted(*GraphicsItemEvent.padding)
        self.textRect.setLeft(x + GraphicsItemShot.iconSize + GraphicsItemEvent.padding[0])
        self.__mouseOver = False
        if self.__class__._ico is None:
            self.__class__._ico = icons.getImage(self.iconName())

    def paint(self, painter, isSelected=False):
        painter.fillRect(self.rect, self.event.color)
        highlightColor = QColor(255, 255, 64, 128)
        if self.__mouseOver == 3:
            painter.fillRect(self.rect, highlightColor)
        elif self.__mouseOver == 1:
            painter.fillRect(QRect(self.rect.x(), self.rect.y(), GraphicsItemEvent.handleWidth, self.rect.height()), highlightColor)
        elif self.__mouseOver == 2:
            painter.fillRect(QRect(self.rect.right() - GraphicsItemEvent.handleWidth + 1, self.rect.y(), GraphicsItemEvent.handleWidth, self.rect.height()), highlightColor)
        if isSelected:
            painter.setPen(Qt.yellow)
            painter.drawRect(self.rect.adjusted(0, 0, -1, -1))
            painter.setPen(Qt.black)
        painter.drawText(self.textRect, 0, self.event.name)
        painter.drawPixmap(self.iconRect, self._ico)

    def focusOutEvent(self):
        dirty = self.__mouseOver != 0
        self.__mouseOver = 0
        return dirty

    def mouseMoveEvent(self, pos):
        mouseOver = self.rect.adjusted(0, 0, -1, -1).contains(pos)

        if mouseOver:
            state = 3
            if self.rect.width() > GraphicsItemEvent.handleWidth * 3:
                lx = pos.x() - self.rect.x()
                if lx < GraphicsItemEvent.handleWidth:
                    state = 1
                elif lx > self.rect.width() - GraphicsItemEvent.handleWidth:
                    state = 2
        else:
            state = 0

        if state != self.__mouseOver:
            self.__mouseOver = state
            return True


class GraphicsItemShot(GraphicsItemEvent):
    @classmethod
    def iconName(cls):
        return 'Film Strip'


class TimelineMarqueeAction(MarqueeActionBase):
    CLICK_SIZE = 2

    def __init__(self, view, selectionModel, undoStack):
        super(TimelineMarqueeAction, self).__init__(view, selectionModel)
        self._undoStack = undoStack

    @staticmethod
    def _preprocess(selectionModel, itemsIter):
        # an items model will tell us what rows are selected in that model
        model = selectionModel.model()
        selectedRows = set(idx.row() for idx in selectionModel.selectedRows())

        # an items model will tell us what change has happened in that model
        touchedRows = set()
        for graphicsItem in itemsIter:
            # add row to right model change
            pyObj = graphicsItem.event
            touchedRows.add(pyObj.items[0].row())

        yield selectionModel, selectedRows, touchedRows

    @staticmethod
    def _selectNew(selectionModels, itemsIter):
        changeMap = {}
        for selectionModel, selectedRows, touchedRows in TimelineMarqueeAction._preprocess(selectionModels, itemsIter):
            keep = selectedRows & touchedRows
            select = (touchedRows - keep)
            deselect = (selectedRows - keep)
            if not select and not deselect:
                continue
            changeMap[selectionModel] = select, deselect
        return changeMap

    @staticmethod
    def _selectAdd(selectionModels, itemsIter):
        changeMap = {}
        for selectionModel, selectedRows, touchedRows in TimelineMarqueeAction._preprocess(selectionModels, itemsIter):
            select = set(x for x in itemsIter) - selectedRows
            if not select:
                continue
            changeMap[selectionModel] = select, set()
        return changeMap

    @staticmethod
    def _selectRemove(selectionModels, itemsIter):
        changeMap = {}
        for selectionModel, selectedRows, touchedRows in TimelineMarqueeAction._preprocess(selectionModels, itemsIter):
            deselect = set(x for x in itemsIter) & selectedRows
            if not deselect:
                continue
            changeMap[selectionModel] = set(), deselect
        return changeMap

    @staticmethod
    def _selectToggle(selectionModels, itemsIter):
        changeMap = {}
        for selectionModel, selectedRows, touchedRows in TimelineMarqueeAction._preprocess(selectionModels, itemsIter):
            deselect = touchedRows & selectedRows
            select = touchedRows - deselect
            if not select and not deselect:
                continue
            changeMap[selectionModel] = select, deselect
        return changeMap

    def _createCommand(self, selectionModels, changeMap):
        """
        # TODO: If we instead were editing one single model, and our other views were just filtered versions of the same model, this can become so much simpler
        Super fun hacky times!
        So the SelectionModelEdit does not actually change anything as it reacts to changes
        by Qt views to a selectionModel. We just retroactively try to make those selection changes undoable.
        If we want to push selection changes, which would work as normal and push undo commands to the stack for free.
        But now we want to push multiple selection changes as 1 undo macro.
        """
        self._undoStack.beginMacro('Multi-selection model edit')
        for selectionModel, change in changeMap.iteritems():

            model = selectionModel.model()
            added = QItemSelection()
            removed = QItemSelection()

            for row in change[0]:
                left = model.index(row, 0)
                right = model.index(row, model.columnCount() - 1)
                added.select(left, right)

            for row in change[1]:
                left = model.index(row, 0)
                right = model.index(row, model.columnCount() - 1)
                removed.select(left, right)

            selectionModel.select(added, QItemSelectionModel.Select)
            selectionModel.select(removed, QItemSelectionModel.Deselect)
        self._undoStack.endMacro()


class TimelineView(GridView):
    def __init__(self, timer, undoStack, model, selectionModel):
        super(TimelineView, self).__init__(mask=1)

        # TODO: these multiple models should become 1 model owned by this view, where the other views are just filtered
        self.__model = model
        self.__selectionModel = selectionModel
        selectionModel.selectionChanged.connect(self.repaint)
        model.dataChanged.connect(self.layout)

        self._timer = timer
        timer.changed.connect(self.repaint)
        self._undoStack = undoStack
        self.setMouseTracking(True)
        self.__graphicsItems = []
        self.frameAll()
        self._viewRect.changed.connect(self.layout)
        self._viewRect.changed.disconnect(self.repaint)  # layout already calls repaint

    def frameAll(self):
        start = float('inf')
        end = float('-inf')
        for pyObj in self.__iterAllItemRows():
            start = min(start, pyObj.start)
            end = max(end, pyObj.end)
        if start == float('inf'):
            start = 0.0
            end = 1.0
        self._viewRect.left = start
        self._viewRect.right = end

    def resizeEvent(self, event):
        self.layout()

    def __iterAllItemRows(self):
        for row in xrange(self.__model.rowCount()):
            yield self.__model.item(row, 0).data()

    def layout(self):
        del self.__graphicsItems[:]
        scaleX = self.width() / (self._viewRect.right - self._viewRect.left)
        for pyObj in self.__iterAllItemRows():
            x = round((pyObj.start - self._viewRect.left) * scaleX)
            w = round((pyObj.end - self._viewRect.left) * scaleX - x)
            isShot = isinstance(pyObj, Shot)
            if isShot:
                item = GraphicsItemShot(pyObj, x, w)
            else:
                item = GraphicsItemEvent(pyObj, x, w)
            self.__graphicsItems.append(item)
        self.repaint()

    def itemsAt(self, x, y, w, h):
        rect = QRect(x, y, w, h)
        for item in self.__graphicsItems:
            if item.rect.contains(rect) or item.rect.intersects(rect):
                yield item

    def _reproject(self, x, y):
        return self.xToT(x), y

    def _selectedItems(self):
        for row in set(idx.row() for idx in self.__selectionModel.selectedRows()):
            yield self.__model.item(row).data()

    def _itemHandleAt(self, itemRect, pos):
        # reimplemented from GraphicsItemEvent.mouseMoveEvent
        # returns a mask for what part of the event is clicked (start=1, right=2, both=3)
        if itemRect.width() > GraphicsItemEvent.handleWidth * 3:
            lx = pos.x() - itemRect.x()
            if lx < GraphicsItemEvent.handleWidth:
                return 1
            elif lx > itemRect.width() - GraphicsItemEvent.handleWidth:
                return 2
        return 3

    def mousePressEvent(self, event):
        if event.modifiers() & Qt.AltModifier:
            super(TimelineView, self).mousePressEvent(event)
            # creating self._action, calling it's mousePressEvent and repainting is handled in base class
            return

        elif event.button() == Qt.RightButton:
            # Right button moves the time slider
            self._action = MoveTimeAction(self._timer.time, self.xToT, functools.partial(self._timer.__setattr__, 'time'))

        elif event.button() == Qt.LeftButton:
            # Drag selected timeline item under mouse
            items = set(self.itemsAt(event.x(), event.y(), 1, 1))
            events = {item.event for item in items}
            selected = set(self._selectedItems())
            if events & selected:
                for item in items:
                    handle = self._itemHandleAt(item.rect, event.pos())
                    break
                self._action = MoveEventAction(self._reproject, self.cellSize, selected, handle)

        if not self._action:
            # else we start a new selection action
            self._action = TimelineMarqueeAction(self, self.__selectionModel, self._undoStack)

        if self._action.mousePressEvent(event):
            self.repaint()

    def mouseMoveEvent(self, event):
        if self._action:
            super(TimelineView, self).mouseMoveEvent(event)
            return

        if event.button():
            return

        dirty = False
        pos = event.pos()
        for item in self.__graphicsItems:
            dirty = dirty or item.mouseMoveEvent(pos)
        if dirty:
            self.repaint()

    def mouseReleaseEvent(self, event):
        action = self._action
        super(TimelineView, self).mouseReleaseEvent(event)  # self._action = None
        # make sure self.action is None before calling mouseReleaseEvent so that:
        # 1. when returning True we will clear any painting done by self.action during mousePress/-Move
        # 2. when a callback results in a repaint the above holds true
        if action and action.mouseReleaseEvent(self._undoStack):
            self.repaint()

    def leaveEvent(self, event):
        dirty = False
        for item in self.__graphicsItems:
            dirty = dirty or item.focusOutEvent()
        if dirty:
            self.repaint()

    def paintEvent(self, event):
        super(TimelineView, self).paintEvent(event)

        selectedPyObjs = {idx.data(Qt.UserRole + 1) for idx in self.__selectionModel.selectedRows()}

        painter = QPainter(self)
        for item in self.__graphicsItems:
            isSelected = item.event in selectedPyObjs
            item.paint(painter, isSelected)

        # paint playhead
        x = self.tToX(self._timer.time)
        drawPlayhead(painter, x, self.height())

        if self._action is not None:
            self._action.draw(painter)
