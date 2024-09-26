import os
from typing import cast

from flex_project.content.project_manager import ProjectManager
from flex_project.rendering.evaluator import Evaluator
from flex_project.content.structure import Project, Template
from flex_project.utils import tt_json5
from flex_project.utils.paths import canonicalAbsolutepath
from flex_project.widgets.camera import CameraEdit
from flex_project.widgets.project_view import ShaderTreeView
from qt import *
from qtutil import QMainWindowState


class Viewport(QOpenGLWindow):
    def __init__(self, projectManager: ProjectManager) -> None:
        super().__init__()
        self.__haveGL = False

        self.__evaluator = Evaluator('')
        self.__templates = {}
        self.__project = Project()
        self.__projectFolder = ''

        self.__sceneShadersFolder = ''
        self.__templateName = ''

        projectManager.projectLoaded.connect(self._update)

    def _update(self, projectManager: ProjectManager):
        self.__templates.clear()
        self.__project = projectManager.project()
        self.__projectFolder = projectManager.projectFolder()

        # TODO: The project manager should manage and hot-reload these templates too
        templatesFolder = os.path.join(projectManager.projectFolder(), 'templates')
        for templateFileName in os.listdir(templatesFolder):
            if not templateFileName.endswith('.json5'):
                continue
            templateName = os.path.splitext(templateFileName)[0]
            templatePath = os.path.join(templatesFolder, templateFileName)
            with open(templatePath, 'rb') as fh:
                self.__templates[templateName] = Template(**tt_json5.parse(tt_json5.SStream(fh.read())))

        if self.__haveGL:
            projectShadersFolder = os.path.join(projectManager.projectFolder(), 'shaders')
            self.__evaluator.initialize(self.__project, self.width(), self.height(), projectShadersFolder)
            self.update()

    def setActiveScene(self, sceneShadersFolder: str, templateName: str):  # TODO: Make a scene object...
        self.__sceneShadersFolder = sceneShadersFolder
        self.__templateName = templateName
        self.update()

    def initializeGL(self):
        self.__haveGL = True
        self.__evaluator.setBackbuffer(self.defaultFramebufferObject())  # TODO: What if this changes?
        projectShadersFolder = os.path.join(self.__projectFolder, 'shaders')
        self.__evaluator.initialize(self.__project, self.width(), self.height(), projectShadersFolder)

    def resizeEvent(self, event):
        self.__evaluator.resize(self.width(), self.height())

    def paintGL(self):
        if not self.__sceneShadersFolder or not self.__templateName:
            return
        templateShadersFolder = os.path.join(self.__projectFolder, 'templates', self.__templateName)
        self.__evaluator.draw(self.__templates[self.__templateName].draw, self.__sceneShadersFolder, templateShadersFolder)

    def closeEvent(self, event):
        self.__evaluator.cleanup()


class App(QMainWindowState):
    def __init__(self, projectFolder: str):
        super().__init__(QSettings('_.ini'))
        self.setDockNestingEnabled(True)

        projectFolder = canonicalAbsolutepath(projectFolder)

        self.__project = ProjectManager()
        self.__shaderTreeView = ShaderTreeView(self.__project)
        self.__viewport = Viewport(self.__project)
        self.__viewport.setActiveScene(os.path.join(projectFolder, 'scenes', 'test'), 'example')
        self.__cameraEdit = CameraEdit()

        self.__window = self.createWindowContainer(self.__viewport, self)
        self.__window.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._addDockWidget(self.__window, 'Viewport', where=Qt.DockWidgetArea.TopDockWidgetArea)
        self._addDockWidget(cast(QWidget, self.__shaderTreeView), 'Scenes', where=Qt.DockWidgetArea.LeftDockWidgetArea)
        self._addDockWidget(self.__cameraEdit, 'Camera', where=Qt.DockWidgetArea.BottomDockWidgetArea)

        self.__project.openProject(projectFolder)


def main(projectFolder: str) -> None:
    app = QApplication([])
    app.setStyle('Fusion')
    win = App(projectFolder)
    win.show()
    app.exec()


if __name__ == '__main__':
    main(os.path.join(QDir.currentPath(), 'test_project'))
