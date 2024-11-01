from dataclasses import dataclass, field
import os
import traceback
from typing import Any, ClassVar

import pyjson5
from qt import QObject, Signal

from plugin_host_app import PluginContext


_PROJECT_EXCLUDED_DIRS: list[str] = ['__pycache__', 'plugins' ]


@dataclass
class Project(object):
    """
    Project entity.
    """
    # Project resource and static initialization definitions.
    version: int = field(default_factory = int)


class UnknownProjectFormatException(Exception): ...
class ProjectLoadingErrorException (Exception): ...


class ProjectManager(QObject):
    """
    Load, unload and monitor Flex projects.
    """

    projectLoaded    : ClassVar[Signal] = Signal()
    projectLoadFailed: ClassVar[Signal] = Signal(str) # Signal(normalizedProjectPath:str).
    projectChanged   : ClassVar[Signal] = Signal(str) # Signal(normalizedFilePath:str).
    __version        : ClassVar[int]    = 0x100 # Current version ID.

    projectName      : str     = None   # Name of the project.
    projectDirtyFlag : bool    = False  # True if there are unsaved changes, False otherwise.
    projectPath      : str     = None   # Absolute path to the project store.
    project          : Project = None   # Project instance.

    __defaultProjectName : ClassVar[str] = "Untitled.smx"

    def __init__(self) -> None:
        """
        Initialize the project manager.
        """
        super().__init__()

        self.projectName = __class__.__defaultProjectName
        self.projectDirtyFlag = False
        self.projectPath = None
        self.project = Project()

    def openProject(self, projectPath: str, rethrowExceptions: bool = False) -> bool:
        """
        Open the project given as argument.
        If there are any errors when loading the project, it is discarded and the operation falls back to the previous
        project.
        A notification is displayed to the user in case of failure.
        Parameters:
            projectPath (str): Path to the project file. Can be either absolute or relative, and contain environment
                variables.
            rethrowExceptions (bool): If True, exceptions are rethrown; otherwise exceptions are captured.
        Returns:
            bool: True if project could be open; False otherwise.
        """
        assert projectPath is not None and len(projectPath.strip()) > 0

        projectPath = PluginContext.normalizedPath(projectPath)
        if self.projectPath != projectPath:
            prevPluginSource = PluginContext.normalizedPath(os.path.join(os.path.dirname(self.projectPath), "plugins")) if self.projectPath else None
            nextPluginSource = PluginContext.normalizedPath(os.path.join(os.path.dirname(projectPath), "plugins"))

        context: PluginContext = PluginContext.instance()
        try:
            if self.projectPath != projectPath:
                if prevPluginSource and os.path.isdir(prevPluginSource):
                    context.unwatchDirectory(prevPluginSource)

                if os.path.isdir(nextPluginSource): 
                    context.addPluginSource (nextPluginSource)
            with open(projectPath, 'r') as fh:
                try:
                    jsonData = fh.read()
                    jsonDict = pyjson5.decode(jsonData)
                    jsonDict = self.__upgradeProject(jsonDict, jsonDict.get("version"), self.__version)
                    project  = Project(**jsonDict)

                except UnknownProjectFormatException as e:
                    raise e

                except Exception as e:
                    if PluginContext.dev():
                        print(f"Exception \"{type(e).__name__}\" ocurred: {e}.")
                    raise ProjectLoadingErrorException()

            if self.projectPath != projectPath:
                context.watchDirectory(PluginContext.normalizedPath(os.path.dirname(projectPath)), self.__projectChanged, _PROJECT_EXCLUDED_DIRS)

            self.projectPath = projectPath
            self.project = project
            self.projectName = os.path.basename(self.projectPath)
            self.projectDirtyFlag = False

            if PluginContext.dev():
                print(f"Loaded project \"{projectPath}\".")
            self.projectLoaded.emit()
            return True

        except Exception as e:
            # If the project was not instantiated correctly, nothing will have
            # changed, and that is ok.
            if self.projectPath != projectPath:
                if os.path.isdir(nextPluginSource): context.removePluginSource(nextPluginSource)
                if prevPluginSource and os.path.isdir(prevPluginSource): context.addPluginSource(prevPluginSource)
            if rethrowExceptions:
                raise e
            else:
                traceback.print_exception(e)
            self.projectLoadFailed.emit(projectPath)
            return False

    def __projectChanged(self, changedItemPath: str) -> None:
        """
        """
        # TODO dc Implementation.
        changedItemPath = PluginContext.normalizedPath(changedItemPath)
        self.projectChanged.emit(changedItemPath)

    def __upgradeProject(self, jsonDict: Any, loadedVersion: int, targetVersion: int) -> Any:
        """
        If loaded project schema is not up to current version, perform the upgrade.
        Upgrade is run upon raw Json data. Project deserialization occurs right after the upgrade.
        Recommended way to implement upgrades is incrementally.
        Parameters:
            jsonDict (Any): Project as a Json dictionary.
            loadedVersion (int): Project schema version indicated in the project file.
            targetVersion (int): Project schema version supported by the application.
        Returns:
            Any: New project Json dictionary according to the schema version supported by this application. 
        Raises:
            UnknownProjectFormatException: project version in unsupported (usually, higher).
        """

        if loadedVersion > targetVersion:
            raise UnknownProjectFormatException()
        if loadedVersion < targetVersion:
            ...
            # ... Version upgrade code goes here ...
        jsonDict["version"] = self.__version
        return jsonDict
