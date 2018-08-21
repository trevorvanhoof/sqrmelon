import functools
from qtutil import *
from experiment.delegates import AtomDelegate
from commands import NodeEditArray
from utils import tableView
from actions import CreateConnectionAction, DragNodeAction
from commands import SetAttr
from model import Plug, OutputPlug, Stitch, Node, EStitchScope
from utils import blankDialog


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

        self._inputList = QTableView()
        tableView(self._inputList, mainLayout, 'input', self._addInput, self._deleteSelectedInputs, self._renameInput)

        self._outputList = QTableView()
        tableView(self._outputList, mainLayout, 'output', self._addOutput, self._deleteSelectedOutputs, self._processOutputChange)
        self._outputList.setSelectionBehavior(QTableView.SelectRows)
        self._outputList.setItemDelegateForColumn(1, AtomDelegate())

        self._stitchList = QTableView()
        tableView(self._stitchList, mainLayout, 'stitch', self._addStitch, self._deleteSelectedStitches, self._processStitchChange)
        self._stitchList.setSelectionBehavior(QTableView.SelectRows)
        self._stitchList.setItemDelegateForColumn(1, AtomDelegate())

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
        with blankDialog(self, 'Add output') as dialog:
            dialog.layout().addWidget(QLabel('New output name'))
            name = QLineEdit()
            dialog.layout().addWidget(name)
            dialog.layout().addWidget(QLabel('Target buffer size\n(negative means factor of resolution)'))
            size = QSpinBox()
            size.setMinimum(-128)
            size.setMaximum(16192)
            dialog.layout().addWidget(size)
        if dialog.result() != QDialog.Accepted or not name.text() or size.value() == 0:
            return
        for plug in self.node.outputs:
            if name.text() == plug.name:
                QMessageBox.critical(None, 'Error', 'Node %s already has an output named %s' % (self.node.name, plug.name))
                return
        plug = OutputPlug(name.text(), self.node, size.value())
        self.undoStack.push(NodeEditArray(self.setNode, self.node.outputs, self.node, [plug], NodeEditArray.Add, self.nodeChanged.emit))

    def _deleteSelectedOutputs(self):
        rows = {idx.row() for idx in self._outputList.selectionModel().selectedRows()}
        mdl = self._outputList.model()
        plugs = [mdl.item(row).data() for row in rows]
        self.undoStack.push(NodeEditArray(self.setNode, self.node.outputs, self.node, plugs, NodeEditArray.Remove, self.nodeChanged.emit))

    def _processOutputChange(self, item):
        plug = self._outputList.model().item(item.row()).data()
        if item.column() == 0:
            name = 'name'
            old = plug.name
            new = item.text()
        else:
            name = 'size'
            old = plug.size
            try:
                new = int(item.text())
            except:
                return
        self.undoStack.push(SetAttr(functools.partial(setattr, plug, name), old, new, self.nodeChanged.emit))

    def _addStitch(self):
        with blankDialog(self, 'Add output') as dialog:
            name = QLineEdit()
            dialog.layout().addWidget(name)
            scope = QComboBox()
            scope.addItems(EStitchScope.options())
            dialog.layout().addWidget(scope)
        if dialog.result() != QDialog.Accepted or not name.text():
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
        stitch = self._stitchList.model().item(item.row()).data()
        if item.column() == 0:
            name = 'name'
            old = stitch.name
            new = item.text()
        else:
            name = 'scope'
            old = stitch.scope
            new = EStitchScope(item.text())
        self.undoStack.push(SetAttr(functools.partial(setattr, stitch, name), old, new, functools.partial(self.setNode, self.node)))

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
            item2 = QStandardItem(str(output.size))
            item2.setData(int)
            mdl.appendRow([item, item2])

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
