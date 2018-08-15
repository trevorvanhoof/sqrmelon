import functools
import json
import uuid

from qtutil import *


def lerp(a, b, t): return (b - a) * t + a


class Plug(object):
    def __init__(self, name, node):
        self.name = name
        self.node = node
        self.connections = []
        self._portRect = None
        self._textRect = None

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

    def setPosition(self, x, y):
        self._rect.move(x, y)
        self._contentRect.move(x + Node.PADDING, y + Node.PADDING)

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
        mainLayout.addWidget(self._inputList)
        self._inputList.dataChanged.connect(self._renameInput)

        addOutput = QPushButton('Add output')
        mainLayout.addWidget(addOutput)
        addOutput.clicked.connect(self._addOutput)
        deleteOutput = QPushButton('Delete selected outputs')
        mainLayout.addWidget(deleteOutput)
        deleteOutput.clicked.connect(self._deleteSelectedOutputs)
        self._outputList = QListView()
        mainLayout.addWidget(self._outputList)
        self._outputList.dataChanged.connect(self._renameOutput)

        addStitch = QPushButton('Add stitch')
        mainLayout.addWidget(addStitch)
        addStitch.clicked.connect(self._addStitch)
        deleteStitch = QPushButton('Delete selected stitches')
        mainLayout.addWidget(deleteStitch)
        deleteStitch.clicked.connect(self._deleteSelectedStitches)
        self._stitchList = QTableView()
        mainLayout.addWidget(self._stitchList)
        self._stitchList.dataChanged.connect(self._processStitchChange)

    def _addInput(self):
        pass

    def _deleteSelectedInputs(self):
        pass

    def _addOutput(self):
        pass

    def _deleteSelectedOutputs(self):
        pass

    def _addStitch(self):
        pass

    def _deleteSelectedStitches(self):
        pass

    def setNode(self, node):
        self.node = node
        self.setEnabled(bool(node))
        if not node: return
        self._nameEdit.setText(node.name)
        self._nameEdit.textChanged.connect(functools.partial(node.__setattr__, 'name'))


class NodeView(QWidget):
    def __init__(self):
        super(NodeView, self).__init__()
        with open('renderpipelinetest.json') as fh:
            self.graph = deserializeGraph(fh)

    def closeEvent(self, event):
        with open('renderpipelinetest.json', 'w') as fh:
            serializeGraph(self.graph, fh)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(QRect(0, 0, self.width(), self.height()), QColor(120, 120, 120))
        painter.setRenderHints(QPainter.Antialiasing)
        for node in self.graph:
            node.paint(painter)


app = QApplication([])
split = QSplitter(Qt.Horizontal)
view = NodeView()
settings = NodeSettings()
split.addWidget(view)
split.addWidget(settings)
split.show()
app.exec_()
