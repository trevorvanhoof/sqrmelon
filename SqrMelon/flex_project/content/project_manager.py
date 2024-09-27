from __future__ import annotations

import os

from flex_project.content.structure import Project
from flex_project.utils import tt_json5
from flex_project.utils.paths import canonicalAbsolutepath
from qt import *


class DeserializeError(Exception): ...


class ProjectManager(QObject):
    projectLoaded = Signal(object)  # Signal(ProjectManager)

    def __init__(self):
        super().__init__()
        self.__projectFolder = ''
        self.__projectWatcher = QFileSystemWatcher()
        self.__project = Project()
        self.__projectWatcher.fileChanged.connect(self._tryReloadProject)

    def project(self) -> Project:
        return self.__project

    def projectFolder(self) -> str:
        return self.__projectFolder

    def openProject(self, projectFolder: str):
        old = self.__projectFolder
        self.__projectFolder = canonicalAbsolutepath(projectFolder)
        try:
            self._reloadProject()
        except DeserializeError:
            # If the project was not instantiated correctly,
            # nothing will have changed and that is OK.
            self.__projectFolder = old
            return
        self.__projectWatcher.removePath(os.path.join(old, 'test_project.json5'))
        self.__projectWatcher.addPath(os.path.join(self.__projectFolder, 'test_project.json5'))

    def _tryReloadProject(self) -> None:
        try:
            self._reloadProject()
        except DeserializeError:
            print('Error reloading project: file not found or parse error or deserialization error.')
            return

    def _reloadProject(self) -> None:
        projectPath = os.path.join(self.__projectFolder, 'test_project.json5')
        with open(projectPath, 'rb') as fh:
            try:
                project = Project(**tt_json5.parse(tt_json5.SStream(fh.read())))
            except Exception:
                raise DeserializeError
        self.__project = project
        self.projectLoaded.emit(self)
