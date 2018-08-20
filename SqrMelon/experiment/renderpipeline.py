import functools
from experiment import projectutil
from experiment.delegates import AtomDelegate
from experiment.enums import EStitchScope
from qtutil import *
import json
import uuid


def deserializeGraph(fileHandle):
    data = json.load(fileHandle)
    graph = []
    uuidMap = {}

    for nodeData in data['graph']:
        node = Node(nodeData['name'], nodeData['x'], nodeData['y'])
        uuidMap[nodeData['uuid']] = node
        graph.append(node)
        for plugData in nodeData['inputs']:
            plug = Plug(plugData['name'], graph[-1])
            uuidMap[plugData['uuid']] = plug
            node.inputs.append(plug)
        for plugData in nodeData['outputs']:
            plug = Plug(plugData['name'], graph[-1])
            uuidMap[plugData['uuid']] = plug
            node.outputs.append(plug)
        for stitchData in nodeData['stitches']:
            stitch = Stitch(stitchData['name'], EStitchScope(stitchData['scope']))
            node.stitches.append(stitch)
        node.layout()

    for nodeData in data['graph']:
        for plugData in nodeData['inputs']:
            plug = uuidMap[plugData['uuid']]
            for uuid in plugData['connections']:
                plug.connections.append(uuidMap[uuid])
        for plugData in nodeData['outputs']:
            plug = uuidMap[plugData['uuid']]
            for uuid in plugData['connections']:
                plug.connections.append(uuidMap[uuid])

    return graph


def serializeGraph(graph, fileHandle):
    data = {'graph': []}
    uuidCache = {}
    for node in graph:
        nodeData = {
            'uuid': str(uuidCache.setdefault(node, uuid.uuid4())),
            'name': node.name,
            'x': node.x,
            'y': node.y,
            'inputs': [],
            'outputs': [],
            'stitches': []
        }
        for input in node.inputs:
            inputData = {
                'uuid': str(uuidCache.setdefault(input, uuid.uuid4())),
                'name': input.name,
                'connections': [str(uuidCache.setdefault(connection, uuid.uuid4())) for connection in input.connections]
            }
            nodeData['inputs'].append(inputData)
        for output in node.outputs:
            inputData = {
                'uuid': str(uuidCache.setdefault(output, uuid.uuid4())),
                'name': output.name,
                'connections': [str(uuidCache.setdefault(connection, uuid.uuid4())) for connection in output.connections]
            }
            nodeData['outputs'].append(inputData)
        for stitch in node.stitches:
            stitchData = {
                'name': stitch.name,
                'scope': str(stitch.scope)
            }
            nodeData['stitches'].append(stitchData)
        data['graph'].append(nodeData)
    json.dump(data, fileHandle)


def lerp(a, b, t): return (b - a) * t + a


class Stitch(object):
    def __init__(self, name, scope=EStitchScope.Public):
        self.name = name
        self.scope = scope


class Plug(object):
    def __init__(self, name, node):
        self.name = name
        self.node = node
        self.connections = []
        self._portRect = None
        self._textRect = None

    @property
    def portRect(self):
        return self._portRect

    @property
    def textRect(self):
        return self._textRect

    def paint(self, painter):
        painter.drawEllipse(self._portRect)
        painter.drawText(self._textRect, Qt.AlignRight | Qt.AlignTop, self.name)


class Node(object):
    def __init__(self, name, x=0, y=0):
        self.name = name
        self.x = x
        self.y = y
        self._rect = None
        self._contentRect = None
        self.inputs = []
        self.outputs = []
        self.stitches = []

    def setName(self, name):
        self.name = name

    def setPosition(self, x, y):
        self.x = x
        self.y = y
        dx = (x - self._rect.x())
        dy = (y - self._rect.y())
        self._rect.moveTo(x, y)
        self._contentRect.moveTo(x + Node.PADDING, y + Node.PADDING)
        for plug in self.inputs + self.outputs:
            x, y = plug._portRect.x() + dx, plug._portRect.y() + dy
            plug._portRect.moveTo(x, y)
            x, y = plug._textRect.x() + dx, plug._textRect.y() + dy
            plug._textRect.moveTo(x, y)

    @property
    def rect(self):
        if self._rect is None:
            self.layout()
        return self._rect

    PADDING = 4

    def layout(self):
        PLUGSIZE = 7

        metrics = QApplication.fontMetrics()
        padding = Node.PADDING
        em = max(PLUGSIZE, metrics.height()) + padding

        lhs = 0.0
        if self.inputs:
            lhs = max(PLUGSIZE + padding + metrics.width(input.name) + padding for input in self.inputs)
        rhs = 0.0
        if self.outputs:
            rhs = max(PLUGSIZE + padding + metrics.width(input.name) + padding for input in self.outputs)
        contentWidth = max(lhs + rhs, metrics.width(self.name))
        self._contentRect = QRect(self.x + padding, self.y + padding, contentWidth, em * (1 + max(len(self.inputs), len(self.outputs))))
        self._rect = QRect(self.x, self.y, contentWidth + 2 * padding, em * (1 + max(len(self.inputs), len(self.outputs))) + 2 * padding)

        contentRect = self._contentRect.adjusted(0, em, 0, 0)
        for i in xrange(max(len(self.inputs), len(self.outputs))):
            o = ((em - padding) - PLUGSIZE) / 2
            if i < len(self.inputs):
                self.inputs[i]._portRect = QRect(contentRect.x(), contentRect.y() + o, PLUGSIZE, PLUGSIZE)
                self.inputs[i]._textRect = QRect(contentRect.x() + PLUGSIZE + padding, contentRect.y(), lhs - (PLUGSIZE + padding), metrics.height())
            if i < len(self.outputs):
                self.outputs[i]._portRect = QRect(contentRect.right() - PLUGSIZE, contentRect.y() + o, PLUGSIZE, PLUGSIZE)
                self.outputs[i]._textRect = QRect(contentRect.right() - rhs, contentRect.y(), rhs - (PLUGSIZE + padding), contentRect.height())
            contentRect.adjust(0, em, 0, 0)

    def paint(self, painter):
        path = QPainterPath()
        path.addRoundedRect(QRectF(self._rect), Node.PADDING, Node.PADDING)
        painter.fillPath(path, QColor(220, 220, 220))
        painter.drawText(self._contentRect, Qt.AlignHCenter | Qt.AlignTop, self.name)
        for input in self.inputs:
            input.paint(painter)
            # connections are bidirectional, so by only painting connections for inputs we cover all of them
            for other in input.connections:
                start = input._portRect.center()
                end = other._portRect.center()
                path = QPainterPath()
                path.moveTo(start)
                path.cubicTo(QPoint(lerp(start.x(), end.x(), 0.5), start.y()), QPoint(lerp(end.x(), start.x(), 0.5), end.y()), end)
                painter.drawPath(path)
        for output in self.outputs:
            output.paint(painter)


class MoveNode(QUndoCommand):
    def __init__(self, node, oldPos, callback, parent=None):
        super(MoveNode, self).__init__('Node moved', parent)
        self.__node = node
        self.__oldPos = oldPos
        self.__newPos = self.__node.x, self.__node.y
        self.__applied = True
        self.__callback = callback

    def redo(self):
        if self.__applied:
            return
        self.__applied = True
        self.__node.setPosition(*self.__newPos)
        self.__callback()

    def undo(self):
        self.__applied = False
        self.__node.setPosition(*self.__oldPos)
        self.__callback()


class AddNode(QUndoCommand):
    def __init__(self, graph, node, triggerRepaint):
        super(AddNode, self).__init__('Add node')
        self.__graph = graph
        self.__node = node
        self.__triggerRepaint = triggerRepaint

    def redo(self):
        self.__graph.append(self.__node)
        self.__triggerRepaint()

    def undo(self):
        self.__graph.remove(self.__node)
        self.__triggerRepaint()


class DeleteNode(QUndoCommand):
    def __init__(self, graph, node):
        super(DeleteNode, self).__init__('Delete node')
        self.__graph = graph
        self.__node = node

    def redo(self):
        self.__graph.remove(self.__node)

    def undo(self):
        self.__graph.append(self.__node)


class ConnectionEdit(QUndoCommand):
    def __init__(self, a, b, triggerRepaint, parent=None):
        super(ConnectionEdit, self).__init__('Connection edit', parent)
        self._triggerRepaint = triggerRepaint
        self._connect = None
        self._disconnect = tuple()
        if a in a.node.inputs:
            if b is None:  # break connections to a
                self._disconnect = tuple((c, a) for c in a.connections)
            else:
                self._connect = b, a
                # disconnect other inputs from a
                self._disconnect = tuple((c, a) for c in a.connections)
        elif b is not None:  # connect b to a
            self._connect = a, b  # connect a to b
            # disconnect other inputs from b
            self._disconnect = tuple((c, b) for c in b.connections)

    def redo(self):
        if self._connect is not None:
            a, b = self._connect
            a.connections.append(b)
            b.connections.append(a)
        for a, b in self._disconnect:
            a.connections.remove(b)
            b.connections.remove(a)
        self._triggerRepaint()

    def undo(self):
        for a, b in self._disconnect:
            a.connections.append(b)
            b.connections.append(a)
        if self._connect is not None:
            a, b = self._connect
            a.connections.remove(b)
            b.connections.remove(a)
        self._triggerRepaint()


class SetAttr(QUndoCommand):
    def __init__(self, setter, restoreValue, newValue, callback, parent=None):
        super(SetAttr, self).__init__('Attribute change', parent)
        self._setter = setter
        self._newValue = newValue
        self._restoreValue = restoreValue
        self._callback = callback

    def redo(self):
        self._setter(self._newValue)
        self._callback()

    def undo(self):
        self._setter(self._restoreValue)
        self._callback()


class NodeEditArray(QUndoCommand):
    Add = True
    Remove = False

    def __init__(self, inspect, array, node, elements, mode, callback, parent=None):
        super(NodeEditArray, self).__init__('Node element add/remove', parent)
        self._inspect = inspect
        self._array = array
        self._node = node
        self._elements = elements
        self._mode = mode
        self._callback = callback

    def redo(self):
        if self._mode == NodeEditArray.Add:
            self._array.extend(self._elements)
        else:
            for element in self._elements:
                self._array.remove(element)
                if isinstance(element, Plug):
                    # clear connections to this plug
                    for entry in element.connections:
                        entry.connections.remove(element)
        self._inspect(self._node)
        self._node.layout()
        self._callback()

    def undo(self):
        if self._mode == NodeEditArray.Add:
            for element in self._elements:
                self._array.remove(element)
        else:
            # TODO: reinsert at right indices, undo/redo now shuffles plugs. It doesn't break but it's confusing to the user.
            self._array.extend(self._elements)
            for element in self._elements:
                if isinstance(element, Plug):
                    # restore connections to this plug
                    for entry in element.connections:
                        entry.connections.append(element)
        self._inspect(self._node)
        self._node.layout()
        self._callback()


class CreateConnectionAction(object):
    def __init__(self, plug, plugAt, triggerRepaint):
        super(CreateConnectionAction, self).__init__()
        self.__plug = plug
        self.__drag = None
        self.__over = None
        self.__plugAt = plugAt
        self._triggerRepaint = triggerRepaint

    def mousePressEvent(self, event):
        pass

    def mouseMoveEvent(self, event):
        self.__drag = event.pos()
        self.__over = self.__plugAt(event.pos())
        return True

    def mouseReleaseEvent(self, undoStack):
        undoStack.push(ConnectionEdit(self.__plug, self.__over, self._triggerRepaint))
        return True

    def draw(self, painter):
        if self.__drag is not None:
            painter.drawLine(self.__plug.portRect.center(), self.__drag)
        painter.setPen(Qt.NoPen)
        painter.setBrush(Qt.green)
        if self.__over is not None:
            painter.drawEllipse(self.__over.portRect)
        painter.drawEllipse(self.__plug.portRect)


class DragNodeAction(object):
    def __init__(self, node, triggerRepaint):
        self.__restore = node.x, node.y
        self.__node = node
        self.__dragStart = None
        self.__triggerRepaint = triggerRepaint

    def mousePressEvent(self, event):
        self.__dragStart = event.pos()

    def mouseMoveEvent(self, event):
        delta = event.pos() - self.__dragStart
        x = self.__restore[0] + delta.x()
        y = self.__restore[1] + delta.y()
        self.__node.setPosition(x, y)
        return True

    def mouseReleaseEvent(self, undoStack):
        undoStack.push(MoveNode(self.__node, self.__restore, self.__triggerRepaint))

    def draw(self, painter):
        pass


class NodeSettings(QWidget):
    nodeChanged = pyqtSignal()

    def __init__(self, undoStack):
        super(NodeSettings, self).__init__()

        self.undoStack = undoStack
        self.setEnabled(False)
        self.node = None

        mainLayout = vlayout()
        self.setLayout(mainLayout)

        self._nameEdit = QLineEdit()
        mainLayout.addWidget(self._nameEdit)

        addInput = QPushButton('Add input')
        mainLayout.addWidget(addInput)
        addInput.clicked.connect(self._addInput)
        deleteInput = QPushButton('Delete selected inputs')
        mainLayout.addWidget(deleteInput)
        deleteInput.clicked.connect(self._deleteSelectedInputs)
        self._inputList = QListView()
        self._inputList.setSelectionMode(QListView.ExtendedSelection)
        self._inputList.setModel(QStandardItemModel())
        mainLayout.addWidget(self._inputList)
        self._inputList.model().itemChanged.connect(self._renameInput)

        addOutput = QPushButton('Add output')
        mainLayout.addWidget(addOutput)
        addOutput.clicked.connect(self._addOutput)
        deleteOutput = QPushButton('Delete selected outputs')
        mainLayout.addWidget(deleteOutput)
        deleteOutput.clicked.connect(self._deleteSelectedOutputs)
        self._outputList = QListView()
        self._outputList.setModel(QStandardItemModel())
        self._outputList.setSelectionMode(QListView.ExtendedSelection)
        mainLayout.addWidget(self._outputList)
        self._outputList.model().itemChanged.connect(self._renameOutput)

        addStitch = QPushButton('Add stitch')
        mainLayout.addWidget(addStitch)
        addStitch.clicked.connect(self._addStitch)
        deleteStitch = QPushButton('Delete selected stitches')
        mainLayout.addWidget(deleteStitch)
        deleteStitch.clicked.connect(self._deleteSelectedStitches)
        self._stitchList = QTableView()
        self._stitchList.setModel(QStandardItemModel())
        self._stitchList.setSelectionBehavior(QTableView.SelectRows)
        self._stitchList.setSelectionMode(QListView.ExtendedSelection)
        self._stitchList.verticalHeader().setVisible(False)
        self._stitchList.horizontalHeader().setVisible(False)
        self._stitchList.setItemDelegateForColumn(1, AtomDelegate())
        mainLayout.addWidget(self._stitchList)
        self._stitchList.model().itemChanged.connect(self._processStitchChange)

    def _addInput(self):
        text, accepted = QInputDialog.getText(self, 'Add input', 'Set new input name')
        if not accepted or not text:
            return
        for plug in self.node.inputs:
            if text == plug.name:
                QMessageBox.critical(None, 'Error', 'Node %s already has an input named %s' % (self.node.name, plug.name))
                return
        plug = Plug(text, self.node)
        self.undoStack.push(NodeEditArray(self.setNode, self.node.inputs, self.node, [plug], NodeEditArray.Add, self.nodeChanged.emit))

    def _deleteSelectedInputs(self):
        rows = {idx.row() for idx in self._inputList.selectionModel().selectedRows()}
        mdl = self._inputList.model()
        plugs = [mdl.item(row).data() for row in rows]
        self.undoStack.push(NodeEditArray(self.setNode, self.node.inputs, self.node, plugs, NodeEditArray.Remove, self.nodeChanged.emit))

    def _renameInput(self, item):
        self.undoStack.push(SetAttr(functools.partial(setattr, item.data(), 'name'), item.data().name, item.text(), self.nodeChanged.emit))

    def _addOutput(self):
        text, accepted = QInputDialog.getText(self, 'Add output', 'Set new output name')
        if not accepted or not text:
            return
        for plug in self.node.outputs:
            if text == plug.name:
                QMessageBox.critical(None, 'Error', 'Node %s already has an output named %s' % (self.node.name, plug.name))
                return
        plug = Plug(text, self.node)
        self.undoStack.push(NodeEditArray(self.setNode, self.node.outputs, self.node, [plug], NodeEditArray.Add, self.nodeChanged.emit))

    def _deleteSelectedOutputs(self):
        rows = {idx.row() for idx in self._outputList.selectionModel().selectedRows()}
        mdl = self._outputList.model()
        plugs = [mdl.item(row).data() for row in rows]
        self.undoStack.push(NodeEditArray(self.setNode, self.node.outputs, self.node, plugs, NodeEditArray.Remove, self.nodeChanged.emit))

    def _renameOutput(self, item):
        self.undoStack.push(SetAttr(functools.partial(setattr, item.data(), 'name'), item.data().name, item.text(), self.nodeChanged.emit))

    def _addStitch(self):
        dialog = QDialog(self)
        dialog.setLayout(vlayout())
        name = QLineEdit()
        dialog.layout().addWidget(name)
        scope = QComboBox()
        scope.addItems(EStitchScope.options())
        dialog.layout().addWidget(scope)
        buttonbar = hlayout()
        buttonbar.addStretch()
        ok = QPushButton('Ok')
        buttonbar.addWidget(ok)
        cancel = QPushButton('Cancel')
        buttonbar.addWidget(cancel)
        dialog.layout().addLayout(buttonbar)
        ok.clicked.connect(dialog.accept)
        cancel.clicked.connect(dialog.reject)
        dialog.exec_()
        if dialog.result() != QDialog.Accepted:
            return
        if not name.text():
            return
        for stitch in self.node.stitches:
            if stitch.name == name.text():
                QMessageBox.critical(None, 'Error', 'Node %s already has a stitch named %s' % (self.node.name, stitch.name))
                return
        stitch = Stitch(name.text(), EStitchScope(scope.currentText()))
        self.undoStack.push(NodeEditArray(self.setNode, self.node.stitches, self.node, [stitch], NodeEditArray.Add, self.nodeChanged.emit))

    def _deleteSelectedStitches(self):
        rows = {idx.row() for idx in self._stitchList.selectionModel().selectedRows()}
        mdl = self._stitchList.model()
        stitches = [mdl.item(row).data() for row in rows]
        self.undoStack.push(NodeEditArray(self.setNode, self.node.stitches, self.node, stitches, NodeEditArray.Remove, self.nodeChanged.emit))

    def _processStitchChange(self, item):
        if item.column() == 0:
            stitch = item.data()
            self.undoStack.push(SetAttr(functools.partial(setattr, stitch, 'name'), stitch.name, item.text(), functools.partial(self.setNode, self.node)))
        elif item.column() == 1:
            stitch = self._stitchList.model().item(item.row()).data()
            self.undoStack.push(SetAttr(functools.partial(setattr, stitch, 'scope'), stitch.scope, EStitchScope(item.text()), functools.partial(self.setNode, self.node)))

    def __onEditingFinished(self, *args):
        self.undoStack.push(SetAttr(functools.partial(setattr, self.node, 'name'), self.node.name, self._nameEdit.text(), self.nodeChanged.emit))

    def setNode(self, node):
        if self.node:
            self._nameEdit.textChanged.disconnect(self.__onEditingFinished)
        self.node = node
        self.setEnabled(bool(node))
        if not node:
            return

        self._nameEdit.setText(node.name)
        self._nameEdit.textChanged.connect(self.__onEditingFinished)

        mdl = self._inputList.model()
        mdl.clear()
        for input in node.inputs:
            item = QStandardItem(input.name)
            item.setData(input)
            mdl.appendRow(item)

        mdl = self._outputList.model()
        mdl.clear()
        for output in node.outputs:
            item = QStandardItem(output.name)
            item.setData(output)
            mdl.appendRow(QStandardItem(item))

        mdl = self._stitchList.model()
        mdl.clear()
        for stitch in node.stitches:
            item = QStandardItem(stitch.name)
            item.setData(stitch)
            item2 = QStandardItem(str(stitch.scope))
            item2.setData(stitch.scope.__class__)
            mdl.appendRow([item, item2])


class NodeView(QWidget):
    currentNodeChanged = pyqtSignal(Node)

    def __init__(self, undoStack, parent=None):
        super(NodeView, self).__init__(parent)
        self._undoStack = undoStack
        self._action = None
        self.graph = []

    def _portAt(self, ignoreNode, pos, attr):
        for node in self.graph:
            if node == ignoreNode:
                continue
            for plug in getattr(node, attr):
                if plug.portRect.contains(pos):
                    return plug
                if plug.textRect.contains(pos):
                    return plug

    def _inputAt(self, ignoreNode, pos):
        return self._portAt(ignoreNode, pos, 'inputs')

    def _outputAt(self, ignoreNode, pos):
        return self._portAt(ignoreNode, pos, 'outputs')

    def mousePressEvent(self, event):
        for node in self.graph:
            if not node.rect.contains(event.pos()):
                continue
            self.currentNodeChanged.emit(node)
            for plug in (node.inputs + node.outputs):
                if plug.portRect.contains(event.pos()):
                    if plug in node.inputs:
                        self._action = CreateConnectionAction(plug, functools.partial(self._outputAt, node), self.repaint)
                    else:
                        self._action = CreateConnectionAction(plug, functools.partial(self._inputAt, node), self.repaint)
                    break
            else:
                self._action = DragNodeAction(node, self.repaint)

        if self._action:
            if self._action.mousePressEvent(event):
                self.repaint()

    def mouseMoveEvent(self, event):
        if self._action:
            if self._action.mouseMoveEvent(event):
                self.repaint()

    def mouseReleaseEvent(self, event):
        action = self._action
        self._action = None
        # make sure self.action is None before calling mouseReleaseEvent so that:
        # 1. when returning True we will clear any painting done by self.action during mousePress/-Move
        # 2. when a callback results in a repaint the above holds true
        if action and action.mouseReleaseEvent(self._undoStack):
            self.repaint()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(QRect(0, 0, self.width(), self.height()), QColor(120, 120, 120))
        painter.setRenderHints(QPainter.Antialiasing)
        for node in self.graph:
            node.paint(painter)
        if self._action:
            self._action.draw(painter)


class RenderPipelineEditor(QMainWindowState):
    def __init__(self):
        super(RenderPipelineEditor, self).__init__(QSettings('PB', 'SqrMelon'))
        menuBar = QMenuBar()
        self.setMenuBar(menuBar)

        fileMenu = menuBar.addMenu('&File')

        a = fileMenu.addAction('&Save')
        a.setShortcut(QKeySequence('Ctrl+S'))
        a.triggered.connect(self.__save)

        a = fileMenu.addAction('&Open')
        a.setShortcut(QKeySequence('Ctrl+O'))
        a.triggered.connect(self.__open)

        fileMenu = menuBar.addMenu('&Edit')

        self.__undoStack = QUndoStack()
        a = self.__undoStack.createUndoAction(self)
        fileMenu.addAction(a)
        a.setShortcut(QKeySequence('Ctrl+Z'))

        a = self.__undoStack.createRedoAction(self)
        fileMenu.addAction(a)
        a.setShortcut(QKeySequence('Ctrl+Shift+Z'))

        a = fileMenu.addAction('&New node')
        a.setShortcut(QKeySequence('Ctrl+N'))
        a.triggered.connect(self.__create)

        a = fileMenu.addAction('&Delete current node')
        a.setShortcut(QKeySequence('Delete'))
        a.triggered.connect(self.__delete)

        self.__view = NodeView(self.__undoStack)
        self.__settings = NodeSettings(self.__undoStack)
        self.__view.currentNodeChanged.connect(self.__settings.setNode)
        self.__settings.nodeChanged.connect(self.__view.repaint)
        self.createDockWidget(self.__view, 'View')
        self.createDockWidget(self.__settings, 'Settings')

        self.__currentGraphFile = None

    def __create(self):
        result = QInputDialog.getText(self, 'Create node', 'Name')
        if not result[0] or not result[1]:
            return
        node = Node(result[0], 0, 0)
        node.layout()
        self.__undoStack.push(AddNode(self.__view.graph, node, self.repaint))

    def __delete(self):
        if self.__settings.node:
            self.__undoStack.append(DeleteNode(self.__view.graph, self.__settings.node))

    def __save(self):
        result = self.currentGraphFile()
        if not result:
            return
        with open(result, 'w') as fh:
            serializeGraph(self.__view.graph, fh)
        QMessageBox.information(self, 'Save successful', 'Saved %s' % result)

    def __open(self):
        result = QFileDialog.getOpenFileName(self, 'Open', self.currentGraphDir(), 'Pipeline files (*.json)')
        if not result:
            return
        self.__undoStack.clear()
        self.__currentGraphFile = result
        with open(result) as fh:
            self.__view.graph = deserializeGraph(fh)
        self.__view.repaint()

    def currentGraphFile(self):
        if self.__currentGraphFile and os.path.exists(self.__currentGraphFile):
            return self.__currentGraphFile

    def currentGraphDir(self):
        currentPath = self.currentGraphFile()
        if currentPath:
            return os.path.dirname(currentPath)
        return projectutil.templateFolder()


settings = projectutil.settings()
defaultProjectDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'defaultproject')
settings.setValue('currentproject', defaultProjectDir)

app = QApplication([])
win = RenderPipelineEditor()
win.show()
app.exec_()
