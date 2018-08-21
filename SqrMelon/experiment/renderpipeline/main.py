from qtutil import *
from experiment import projectutil
from commands import AddNode, DeleteNode
from model import Node
from utils import menuAction
from widgets import NodeView, NodeSettings
from fileio import deserializeGraph, serializeGraph


class RenderPipelineEditor(QMainWindowState):
    def __init__(self):
        super(RenderPipelineEditor, self).__init__(QSettings('PB', 'SqrMelon'))
        menuBar = QMenuBar()
        self.setMenuBar(menuBar)

        self.__undoStack = QUndoStack()

        fileMenu = menuBar.addMenu('&File')
        menuAction(fileMenu, '&Save', 'Ctrl+S', self.__save)
        menuAction(fileMenu, '&Open', 'Ctrl+O', self.__open)

        editMenu = menuBar.addMenu('&Edit')
        undo = self.__undoStack.createUndoAction(self)
        editMenu.addAction(undo)
        undo.setShortcut(QKeySequence('Ctrl+Z'))

        redo = self.__undoStack.createRedoAction(self)
        editMenu.addAction(redo)
        redo.setShortcut(QKeySequence('Ctrl+Shift+Z'))

        menuAction(editMenu, '&New node', 'Ctrl+N', self.__create)
        menuAction(editMenu, '&Delete current node', 'Delete', self.__delete)

        self.__view = NodeView(self.__undoStack)
        self.createDockWidget(self.__view, 'View')

        self.__settings = NodeSettings(self.__undoStack)
        self.createDockWidget(self.__settings, 'Settings')

        self.__view.currentNodeChanged.connect(self.__settings.setNode)
        self.__settings.nodeChanged.connect(self.__view.repaint)
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
            self.__undoStack.push(DeleteNode(self.__view.graph, self.__settings.node, self.repaint))

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


if __name__ == '__main__':
    # demo it
    settings = projectutil.settings()
    defaultProjectDir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'defaultproject')
    settings.setValue('currentproject', defaultProjectDir)

    app = QApplication([])
    win = RenderPipelineEditor()
    win.show()
    app.exec_()
