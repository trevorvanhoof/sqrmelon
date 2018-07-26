from qtutil import *


class SelectionSet(object):
    def __init__(self):
        self.__selection = set()
        self.changed = Signal()

    def __iter__(self):
        for item in self.__selection:
            yield item

    def __contains__(self, item):
        return item in self.__selection

    def __ior__(self, modification):
        self.__selection |= modification
        self.changed.emit()
        return self

    def __isub__(self, modification):
        self.__selection -= modification
        self.changed.emit()
        return self

    def __or__(self, modification):
        return self.__selection | modification

    def __and__(self, modification):
        return self.__selection & modification

    def __sub__(self, modification):
        return self.__selection - modification

    def raw(self):
        return self.__selection


class RecursiveCommandError(Exception):
    pass


class NestedCommand(QUndoCommand):
    stack = []
    isUndo = False

    def __init__(self, label, parent=None):
        # if signal responses to undo() create additional commands we avoid creation
        if NestedCommand.isUndo:
            raise RecursiveCommandError()
        # if signal responses to redo() create additional commands we group them
        if NestedCommand.stack and parent is None:
            parent = NestedCommand.stack[-1]
        self.canPush = parent is None
        super(NestedCommand, self).__init__(label, parent)

    def _redoInternal(self):
        raise NotImplementedError()

    def _undoInternal(self):
        raise NotImplementedError()

    def redo(self):
        NestedCommand.stack.append(self)
        self._redoInternal()
        super(NestedCommand, self).redo()
        NestedCommand.stack.pop(-1)

    def undo(self):
        NestedCommand.isUndo = True
        self._undoInternal()
        super(NestedCommand, self).undo()
        NestedCommand.isUndo = False


class SelectionChangeCommand(NestedCommand):
    def __init__(self, selectionModel, add, remove):
        super(SelectionChangeCommand, self).__init__('Selection change')
        self.__selectionModel = selectionModel
        self.__add = add
        self.__remove = remove
        # validate
        # for item in add:
        #     assert item not in selectionModel
        #     assert item not in remove
        # for item in remove:
        #     assert item in selectionModel
        #     assert item not in add

    def _redoInternal(self):
        oldState = self.__selectionModel.changed.suspend()
        self.__selectionModel |= self.__add
        if oldState:
            self.__selectionModel.changed.resume()
        self.__selectionModel -= self.__remove

    def _undoInternal(self):
        oldState = self.__selectionModel.changed.suspend()
        self.__selectionModel |= self.__remove
        if oldState:
            self.__selectionModel.changed.resume()
        self.__selectionModel -= self.__add


class MarqueeAction(object):
    def __init__(self, itemsAt, selectionModel):
        self.__itemsAt = itemsAt
        self.__selectionModel = selectionModel

    def mousePressEvent(self, event):
        self.__start = event.pos()
        self.__end = event.pos()
        self.__mode = event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier)

    def _rect(self):
        x0, x1 = self.__start.x(), self.__end.x()
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = self.__start.y(), self.__end.y()
        y0, y1 = min(y0, y1), max(y0, y1)
        return x0, y0, max(1, x1 - x0), max(1, y1 - y0)

    def mouseReleaseEvent(self, undoStack):
        x, y, w, h = self._rect()

        mask = set(x for x in self.__itemsAt(x, y, w, h))

        add, remove = set(), set()
        if self.__mode == Qt.NoModifier:
            # clear and set
            # add all not selected yet
            add = mask - self.__selectionModel.raw()
            # deselect all not in the mask
            remove = self.__selectionModel - mask

        elif self.__mode == Qt.ControlModifier | Qt.ShiftModifier:
            # force-add
            # add all not selected yet
            add = mask - self.__selectionModel.raw()

        elif self.__mode == Qt.ControlModifier:
            # force-remove
            # deselect selected items in the mask
            remove = mask & self.__selectionModel.raw()

        else:  # if self.mode == Qt.ShiftModifier:
            # toggle
            # add all not selected yet
            add = mask - self.__selectionModel.raw()
            # deselect selected items in the mask
            remove = mask & self.__selectionModel.raw()

        # if we don't plan to change anything, stop right here and don't submit this undoable action
        if not add and not remove:
            return True

        try:
            cmd = SelectionChangeCommand(self.__selectionModel, add, remove)
            if cmd.canPush:
                undoStack.push(cmd)
            else:
                cmd.redo()
        except RecursiveCommandError:
            pass

    def mouseMoveEvent(self, event):
        self.__end = event.pos()
        return True

    def draw(self, painter):
        x, y, w, h = self._rect()
        painter.setPen(QColor(0, 160, 255, 255))
        painter.setBrush(QColor(0, 160, 255, 64))
        painter.drawRect(x, y, w, h)


class MyListWidget(QWidget):
    def __init__(self, undoStack, parent=None):
        super(MyListWidget, self).__init__(parent)
        self._model = []
        self._selectionModel = SelectionSet()
        self._selectionModel.changed.connect(self.repaint)
        self._action = None
        self._undoStack = undoStack
        self.setFocusPolicy(Qt.StrongFocus)

    @property
    def model(self):
        return self._model

    @property
    def selectionModel(self):
        return self._selectionModel

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(QRect(0, 0, self.width(), self.height()), QColor(255, 255, 255, 255))

        for item, rect in self.__iterItems():
            if item in self._selectionModel:
                painter.fillRect(rect, QColor(0, 0, 0, 128))
            painter.drawText(rect, 0, str(item))

        if self._action is not None:
            self._action.draw(painter)

    def __iterItems(self):
        LINE_HEIGHT = 16
        rect = QRect(0, 0, self.width(), LINE_HEIGHT)
        for item in self._model:
            yield item, rect
            rect.moveTop(rect.y() + LINE_HEIGHT)

    def __itemsAt(self, x, y, w, h):
        bounds = QRect(x, y, w, h)
        for item, rect in self.__iterItems():
            if rect.intersects(bounds):
                yield item

    def mousePressEvent(self, event):
        self._action = MarqueeAction(self.__itemsAt, self._selectionModel)
        if self._action.mousePressEvent(event):
            self.repaint()

    def mouseReleaseEvent(self, event):
        action = self._action
        self._action = None
        # make sure self.action is None before calling mouseReleaseEvent so that:
        # 1. when returning True we will clear any painting done by self.action during mousePress/-Move
        # 2. when a callback results in a repaint the above holds true
        if action and action.mouseReleaseEvent(self._undoStack):
            self.repaint()

    def mouseMoveEvent(self, event):
        if self._action:
            if self._action.mouseMoveEvent(event):
                self.repaint()


class Container(object):
    def __init__(self, name):
        self.name = name
        self.content = [name + 'Child0', name + 'Child1']

    def __str__(self):
        return self.name

    def __iter__(self):
        for item in self.content:
            yield item


class MyListWidget2(MyListWidget):
    def __init__(self, parentMask, undoStack, parent=None):
        super(MyListWidget2, self).__init__(undoStack, parent)
        self._parentMask = parentMask
        parentMask.changed.connect(self.pullContainer)

    def pullContainer(self):
        # get first selected container
        container = tuple()  # empty stub
        for container in self._parentMask: break
        if self._model == container:
            return
        self._model = container

        try:
            add = set(x for x in self._model)
            remove = self._selectionModel - add
            add -= self._selectionModel.raw()
            if not add and not remove:
                self.repaint()
                return
            cmd = SelectionChangeCommand(self._selectionModel, add, remove)
            if cmd.canPush:
                self._undoStack.push(cmd)
            else:
                cmd.redo()
        except RecursiveCommandError:
            pass


class MyListWidget3(MyListWidget):
    def __init__(self, parentMask, undoStack, parent=None):
        super(MyListWidget3, self).__init__(undoStack, parent)
        self._parentMask = parentMask
        parentMask.changed.connect(self.pullContainer)

    def pullContainer(self):
        # get first selected container
        self._model = []
        for x in self._parentMask:
            self._model += list(x)

        try:
            remove = self._selectionModel - set(self._model)
            if not remove:
                self.repaint()
                return
            cmd = SelectionChangeCommand(self._selectionModel, set(), remove)
            if cmd.canPush:
                self._undoStack.push(cmd)
            else:
                cmd.redo()
        except RecursiveCommandError:
            pass


if __name__ == '__main__':
    a = QApplication([])

    undoStack = QUndoStack()
    undoView = QUndoView(undoStack)

    clipList = MyListWidget(undoStack)
    clipList.model.append(Container('Container0'))
    clipList.model.append(Container('Container1'))

    curveList = MyListWidget2(clipList.selectionModel, undoStack)

    keyList = MyListWidget3(curveList.selectionModel, undoStack)

    mainContainer = QSplitter(Qt.Vertical)
    mainContainer.addWidget(undoView)
    mainContainer.addWidget(clipList)
    mainContainer.addWidget(curveList)
    mainContainer.addWidget(keyList)

    mainWindow = QMainWindow()
    mainWindow.setCentralWidget(mainContainer)
    mainWindow.show()
    # makes sure qt cleans up & python stops after closing the main window; https://stackoverflow.com/questions/39304366/qobjectstarttimer-qtimer-can-only-be-used-with-threads-started-with-qthread
    mainWindow.setAttribute(Qt.WA_DeleteOnClose)

    a.exec_()
