import os

from flex_project.content.project_manager import ProjectManager
from qt import *


class ProjectModel(QSortFilterProxyModel):
    def __init__(self) -> None:
        super().__init__()
        model = QFileSystemModel()
        model.setNameFilters(['*.glsl'])
        model.setNameFilterDisables(False)
        model.setFilter(QDir.Filter.NoDotAndDotDot | QDir.Filter.Files | QDir.Filter.AllDirs)
        self.setSourceModel(model)


class ShaderTreeView(QTreeView):
    def __init__(self, projectManager: ProjectManager):
        super().__init__()

        model = ProjectModel()
        self.setModel(model)

        self.setColumnHidden(1, True)
        self.setColumnHidden(2, True)
        self.setColumnHidden(3, True)
        self.setHeaderHidden(True)

        projectManager.projectLoaded.connect(self._update)
        self._update(projectManager)

    def _update(self, projectManager: ProjectManager):
        model = self.model().sourceModel()
        model.setRootPath(projectManager.projectFolder())
        index = self.model().mapFromSource(model.index(model.rootPath()))
        self.setRootIndex(index)

    def mouseDoubleClickEvent(self, event):
        index = self.indexAt(event.pos())
        index = self.model().mapToSource(index)
        path = self.model().sourceModel().filePath(index)
        os.startfile(path)

    def showEvent(self, event):
        # TODO: Figure out how to see for the file system model to be
        #   done fetching children and erspond to that instead.
        QTimer.singleShot(300, self.expandAll)
        QTimer.singleShot(600, self.expandAll)
