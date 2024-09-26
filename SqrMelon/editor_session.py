from __future__ import annotations

from enum import Enum
import os
from pathlib import Path
import sys
from typing import Callable, List
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox, QMainWindow
from qt import QFont, QFontDatabase

class EditorSession:
    """
    Editor session context.
    """

    __versionId: int = 0x100 # Current version ID.
    __dataPath  : str = os.path.join(os.getenv('ProgramData', 'C:\\ProgramData') if os.name == 'nt' else Path('/usr/local/share'), "SqrMelonFx").replace('\\', '/')
    __resourcesPath: str = os.path.join(os.path.dirname(__file__), "resources").replace('\\', '/')

    def __init__(self) -> None:

        self.__defaultProjectName = "Untitled.smx"
        self.__projectName        = self.__defaultProjectName
        self.__isProjectDirty     = True
        self.__projectFn          = None
        self.__onExitCallbacks    : List[Callable[[EditorSession], None]] = []
        self.__variableWidthFont  = None
        self.__monospaceFont      = None
        self.__settings           = self.__tryInstallDefaults(self.__dataPath, self.__resourcesPath)
        self.__loadedVersionId    = self.__settings.value("version", EditorSession.__versionId)
        self.__loadFont("Teko-Regular.ttf")
        self.__mainWindow         = None

        print("Version 0x{:04x}.".format(EditorSession.__versionId))
        print("Using data path \"{}\".".format(self.__dataPath ))

    def finalize(self) -> None:
        for thisCallback in self.__onExitCallbacks:
            thisCallback(self)

    def registerOnExit  (self, callback: Callable[[EditorSession], None]) -> None: self.__onExitCallbacks.append(callback)
    def projectName     (self) -> str : return self.__projectFn if self.__projectFn is not None else self.__projectName
    def isProjectDirty  (self) -> bool: return self.__isProjectDirty
    def settings        (self) -> QSettings: return  self.__settings
    def loadedVersionId (self) -> int : return self.__loadedVersionId

    def monospaceFont   (self, scale: float = 1) -> QFont:
        """
        Get the font to use for fixed width text (e.g., log, code editor, etc.).
        Parameters:
            scale : Font scale multiplier.
        Returns:
            QFont : Font.
        """
        
        if  self.__monospaceFont is None:
            self.__monospaceFont = QFont(self.__loadFont("Inconsolata-Regular.ttf"), self.fontPointSize * scale)
        return self.__monospaceFont

    def defaultFont     (self, scale: float = 1) -> QFont:
        """
        Get the font to use for variable width text.
        Parameters:
            scale : Font scale multiplier.
        Returns:
            QFont : Font.
        """
        if  self.__variableWidthFont is None:
            self.__variableWidthFont = QFont(self.__loadFont("Roboto-Regular.ttf" ), self.fontPointSize * scale)
        return self.__variableWidthFont

    def registerMainWindow  (self, window: QMainWindow) -> None: self.__mainWindow = window
    def unregisterMainWindow(self) -> None: self.__mainWindow = None

    @property
    def fontPointSize(self) -> float: return QFont().pointSizeF()
    @property
    def dataDir      (self) -> str :  return self.__dataPath
    @property
    def resourcesDir (self) -> str :  return self.__resourcesPath

    # TODO The name of __tryInstallDefaults is not really ideal for what the method does.
    def __tryInstallDefaults(self, dataPath: str, resourcesPath: str) -> QSettings:
        """
        For new installments, install defaults.
        Settings is retrieved.
        Parameters:
            dataPath : Path shared across all instances of the application.
            resourcesPath: Resources directory.
        Returns:
            QSettings: Current settings.
        """

        assert dataPath is not None and len(dataPath) > 0
        try:
            if not os.path.isdir(dataPath):
                os.makedirs(dataPath)

            settings = QSettings(os.path.join(dataPath, "SqrMelonFx.ini").replace('\\', '/'), QSettings.IniFormat)
            settings.setValue("version", EditorSession.__versionId)
            settings.setValue("editorInstallDir",  Path(os.path.dirname(os.path.abspath(__file__))).__str__().replace('\\', '/'))        

            # Development defaults.
            if os.getenv("PYTHON_ENV") == "development":
                if  settings.value("lastProjectOpen" , None) is None:
                    settings.setValue("lastProjectOpen", os.path.join(resourcesPath, "default_project", "default_project.smx").replace('\\', '/'))

            return settings

        except:
            # Installing defaults and reading settings is mandatory to operate.
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Critical)
            msgBox.setWindowTitle("Critical error")
            msgBox.setText("SqrMelon Fx couldn't be started.")
            msgBox.setInformativeText("An error occurred when installing required data to \"{}\". Check filesystem permissions and retry.".format(dataPath))
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec()
            sys.exit(-1000)

    def __loadFont(self, fontName: str) -> str:
        """
        Load the font file from "resources" directory.
        Parameters:
            fontName: Name of the font file.
        Returns:
            str: Font family ID.
        """
        path = os.path.join(os.path.dirname(__file__), "resources", fontName).replace('\\', '/')
        if not os.path.isfile(path):
            raise Exception('Font file not found: "%s".'    % fontName)
        fontId = QFontDatabase.addApplicationFont(path)
        if fontId == -1:
            raise Exception('Error loading font file "%s".' % fontName)
        fontFamilies = QFontDatabase.applicationFontFamilies (fontId  )
        if not fontFamilies:
            raise Exception('Error loading font file "%s".' % fontName)
        return fontFamilies[0]
