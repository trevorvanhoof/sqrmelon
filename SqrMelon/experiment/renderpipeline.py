from experiment.delegates import AtomDelegate
from experiment.enums import EStitchScope
from qtutil import *
import json
import uuid


def lerp(a, b, t): return (b - a) * t + a


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

    def paint(self, painter):
        painter.drawEllipse(self._portRect)
        painter.drawText(self._textRect, Qt.AlignRight | Qt.AlignTop, self.name)


class Stitch(object):
    def __init__(self, name, scope=EStitchScope.Public):
        self.name = name
        self.scope = scope


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
                self.inputs[i]._textRect = QRect(contentRect.x() + PLUGSIZE + padding, contentRect.y(), lhs - (PLUGSIZE + padding), contentRect.height())
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


def deserializeGraph(filePath):
    data = json.load(filePath)
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


def serializeGraph(graph, filePath):
    data = {'graph': []}
    uuidCache = {}
    for node in graph:
        nodeData = {
            'uuid': str(uuidCache.setdefault(node, uuid.uuid4())),
            'name': node.name,
            'x': node.x,
            'y': node.y,
            'inputs': [],
            'outputs': []
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
        data['graph'].append(nodeData)
    json.dump(data, filePath)


class NodeSettings(QWidget):
    nodeChanged = pyqtSignal()

    def __init__(self):
        super(NodeSettings, self).__init__()

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
        plug = Plug(text, self.node)
        self.node.inputs.append(plug)
        item = QStandardItem(plug.name)
        item.setData(plug)
        self._inputList.model().appendRow(item)
        self.node.layout()

    def _deleteSelectedInputs(self):
        rows = {idx.row() for idx in self._inputList.selectionModel().selectedRows()}
        mdl = self._inputList.model()
        for row in reversed(sorted(list(rows))):
            plug = mdl.item(row).data()
            self.node.inputs.remove(plug)
            for connection in plug.connections:
                connection.connections.remove(plug)
            self.node.layout()
            mdl.removeRows(row, 1)
        self.nodeChanged.emit()

    def _renameInput(self, item):
        item.data().name = item.text()
        self.nodeChanged.emit()

    def _addOutput(self):
        text, accepted = QInputDialog.getText(self, 'Add output', 'Set new output name')
        if not accepted or not text:
            return
        self.node.outputs.append(Plug(text, self.node))
        self.node.layout()

    def _deleteSelectedOutputs(self):
        rows = {idx.row() for idx in self._outputList.selectionModel().selectedRows()}
        mdl = self._outputList.model()
        for row in reversed(sorted(list(rows))):
            plug = mdl.item(row).data()
            self.node.outputs.remove(plug)
            for connection in plug.connections:
                connection.connections.remove(plug)
            self.node.layout()
            mdl.removeRows(row, 1)
        self.nodeChanged.emit()

    def _renameOutput(self, item):
        item.data().name = item.text()
        self.nodeChanged.emit()

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
        stitch = Stitch(name.text(), EStitchScope(scope.currentText()))
        self.node.stitches.append(stitch)
        mdl = self._stitchList.model()
        item = QStandardItem(stitch.name)
        item.setData(stitch)
        item2 = QStandardItem(str(stitch.scope))
        item2.setData(stitch.scope.__class__)
        mdl.appendRow([item, item2])

    def _deleteSelectedStitches(self):
        rows = {idx.row() for idx in self._stitchList.selectionModel().selectedRows()}
        mdl = self._stitchList.model()
        for row in reversed(sorted(list(rows))):
            stitch = mdl.item(row).data()
            self.node.stitches.remove(stitch)
            mdl.removeRows(row, 1)
        self.nodeChanged.emit()

    def _processStitchChange(self, item):
        if item.column() == 0:
            stitch = item.data()
            stitch.name = item.text()
        elif item.column() == 1:
            stitch = self._stitchList.model().item(item.row()).data()
            stitch.scope = EStitchScope(item.text())

    def __onEditingFinished(self, *args):
        self.node.name = self._nameEdit.text()
        self.nodeChanged.emit()

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


class MoveNode(QUndoCommand):
    def __init__(self, node, oldPos, parent=None):
        super(MoveNode, self).__init__('Node moved', parent)
        self.__node = node
        self.__oldPos = oldPos
        self.__newPos = self.__node.x, self.__node.y
        self.__applied = True

    def redo(self):
        if self.__applied:
            return
        self.__applied = True
        self.__node.setPosition(*self.__newPos)

    def undo(self):
        self.__applied = False
        self.__node.setPosition(*self.__oldPos)


class CreateConnectionAction(object):
    def __init__(self, plug):
        super(CreateConnectionAction, self).__init__()
        self.__plug = plug

    def mousePressEvent(self, event):
        return True

    def mouseMoveEvent(self, event):
        return True

    def mouseReleaseEvent(self, undoStack):
        return True

    def draw(self, painter):
        painter.setPen(Qt.NoPen)
        painter.setBrush(Qt.green)
        painter.drawEllipse(self.__plug.portRect)


class DragNodeAction(object):
    def __init__(self, node):
        self.__restore = node.x, node.y
        self.__node = node
        self.__dragStart = None

    def mousePressEvent(self, event):
        self.__dragStart = event.pos()

    def mouseMoveEvent(self, event):
        delta = event.pos() - self.__dragStart
        x = self.__restore[0] + delta.x()
        y = self.__restore[1] + delta.y()
        self.__node.setPosition(x, y)
        return True

    def mouseReleaseEvent(self, undoStack):
        undoStack.push(MoveNode(self.__node, self.__restore))

    def draw(self, painter):
        pass


class NodeView(QWidget):
    currentNodeChanged = pyqtSignal(Node)

    def __init__(self, undoStack, parent=None):
        super(NodeView, self).__init__(parent)
        self._undoStack = undoStack
        self._action = None
        with open('renderpipelinetest.json') as fh:
            self.graph = deserializeGraph(fh)

    def save(self):
        with open('renderpipelinetest.json', 'w') as fh:
            serializeGraph(self.graph, fh)

    def mousePressEvent(self, event):
        for node in self.graph:
            if not node.rect.contains(event.pos()):
                continue
            self.currentNodeChanged.emit(node)
            for plug in (node.inputs + node.outputs):
                if plug.portRect.contains(event.pos()):
                    self._action = CreateConnectionAction(plug)
                    break
            else:
                self._action = DragNodeAction(node)

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


# TODO: Connect & disconnect, save & load actions
app = QApplication([])
split = QSplitter(Qt.Horizontal)
undoStack = QUndoStack()
view = NodeView(undoStack)
settings = NodeSettings()
view.currentNodeChanged.connect(settings.setNode)
settings.nodeChanged.connect(view.repaint)
split.addWidget(view)
split.addWidget(settings)
split.show()
app.exec_()
