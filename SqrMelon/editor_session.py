from __future__ import annotations

from abc import abstractmethod
from enum import Enum
import os
from pathlib import Path
import sys
from typing import Callable, List, Tuple
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox, QMainWindow
from qt import QFont, QFontDatabase
from pyqttoast import Toast, ToastPreset

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
        self.__undoRedoExecStack  = _UndoRedoExecStack()

        print("Version 0x{:04x}.".format(EditorSession.__versionId))
        print("Using data path \"{}\".".format(self.__dataPath ))
        Toast.setMaximumOnScreen(5)

    def finalize(self) -> None:

        for thisCallback in self.__onExitCallbacks:
            thisCallback(self)

    def issueCommand(self, command: EditorCommandBase) -> bool:
        """
        Execute the command and post it to the undo/redo stack.
        Returns:
            bool: True if the operation succeeded; False otherwise.
        """        
        assert command is not None
        result = self.__undoRedoExecStack.exec(command)
        if isinstance(result, bool):
            if not result:
                self.displayErrorToastNotification("Action failed", "Something went wrong. Please try again.")
            return result
        elif isinstance(result, Tuple[bool, str]):
            if result[1] is not None and len(result[1] > 0):
                if result[0]:
                    self.displaySuccessToastNotification("Action succeeded", result[1])
                else:
                    self.displayErrorToastNotification("Action failed", result[1])
        return result

    def undoPrevCommand(self) -> bool:
        """
        If possible, undo the command pointed by the undo/redo stack.
        If there is nothing to undo, a message will be displayed to the user.
        Returns:
            bool: True if there is nothing to undo or undoing succeeded;
            False otherwise.
        """        
        if (self.__undoRedoExecStack.canUndo()):
            return self.__undoRedoExecStack.undo()
        else:
            self.displayWarningToastNotification("Action not available", "Nothing to undo.")
            return True

    def redoNextCommand(self) -> bool:
        """
        If possible, redo the next command in the undo/redo stack.
        If there is nothing to redo, a message will be displayed to the user.
        Returns:
            bool: True if there is nothing to redo or redoing succeeded;
            False otherwise.
        """

        if (self.__undoRedoExecStack.canRedo()):
            return self.__undoRedoExecStack.redo()
        else:
            self.displayWarningToastNotification("Action not available", "Nothing to redo.")
            return True

    def displaySuccessToastNotification    (self, title: str, mesg: str, duration: int = 4000) -> None: self.__displayToastNotification(title, mesg, duration, ToastPreset.SUCCESS_DARK)
    def displayInformationToastNotification(self, title: str, mesg: str, duration: int = 4000) -> None: self.__displayToastNotification(title, mesg, duration, ToastPreset.INFORMATION_DARK)
    def displayWarningToastNotification    (self, title: str, mesg: str, duration: int = 4000) -> None: self.__displayToastNotification(title, mesg, duration, ToastPreset.WARNING_DARK)
    def displayErrorToastNotification      (self, title: str, mesg: str, duration: int = 8000) -> None: self.__displayToastNotification(title, mesg, duration, ToastPreset.ERROR_DARK)
    def __displayToastNotification(self, title: str, mesg: str, duration: int, preset: ToastPreset) -> None:

        toast = Toast(self.__mainWindow)
        toast.setMinimumWidth(200)
        toast.setMinimumHeight(100)
        toast.setTitle (title)
        toast.setText(mesg)
        toast.setBorderRadius(3)
        toast.applyPreset(preset)
        toast.show()

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

    def registerMainWindow  (self, window: QMainWindow) -> None: 

        self.__mainWindow = window
        Toast.setPositionRelativeToWidget(window)

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

class EditorCommandBase(object):
    """
    All actions operated by the user that change the state of the project
    in memory are processed through commands that are stacked in the undo/redo
    stack.
    Commands can be traversed anytime to inspect and operate on them.
    Payload must be provided by you and the command is responsible of
    referencing the payload data needed to operate durint its lifetime.
    When we say "that change the state of the project", we refer to operations
    that will have some impact in the exported result (e.g., changing the
    value of a key in the Curve Editor).
    Things modified using external tools (like shader source code changes) are
    not to be tracked.
    """

    @abstractmethod
    def exec(self) -> bool | Tuple[bool, str]:
        """
        Execute the command.
        This function is a callback and shouldn't be called directly.
        To process this command, call EditorSession.issueCommand().
        Returns:
            bool: True if the operation succeeded; False otherwise.
            Tuple[bool, str]: If you need to bring a message to the 
            user, this tuple contains both a bool determining whether the
            operation succeeded or not, and a string with the message
            you want to display. Message will be displayed in the form of
            a toast notification to the user.
        """

    @abstractmethod
    def undo(self) -> bool:
        """
        Implement to undo this command.
        This function is a callback and shouldn't be called directly.
        To undo this command, call EditorSession.undoLastCommand().
        Returns:
            bool: True if the operation succeeded; False otherwise.
        """
        pass

    @abstractmethod
    def redo(self) -> bool:
        """
        Implement to redo this command.
        Most of the times, it'll safe reusing exec() here.
        This function is a callback and shouldn't be called directly.
        To redo this command, call EditorSession.redoNextCommand().
        Returns:
            bool: True if the operation succeeded; False otherwise.
        """
        pass

    def displayName(self) -> str:
        """
        Get the display name to be displayed when communicating with the user.
        Returns:
            str: Display name (defaults to class name if not overriden).
        """
        return __class__.name()

class _UndoRedoExecStack(object):
    """
    This class handles execution, undoing and redoing of EditorCommandBase 
    instances. Internally, it is implemented in the form of circular list,
    and behaves like a general undo/redo stack in every application.
    """
    
    __FIXED_STACK_CAPACITY = 3 # 512

    class __NopEditorCommand(EditorCommandBase):
        def exec(self) -> bool: return True
        def undo(self) -> bool: return True
        def redo(self) -> bool: return True

    def __init__(self):

        super().__init__()
        self.clearUndoRedoStack()

    def exec(self, command: EditorCommandBase) -> bool:
        """
        Execute the command and add it to the undo/redo stack if execution
        succeeds.
        Parameters:
            command: The command to execute.
        Returns:
            True if execution succeeded, False otherwise.
        """

        result = command.exec()
        if result:
            self.__stackPtr  = self.__stackTop = self.__stackPtr + 1
            self.__stackBase = max(0, self.__stackPtr - __class__.__FIXED_STACK_CAPACITY)
            self.__stack[(self.__stackPtr - 1) % __class__.__FIXED_STACK_CAPACITY] = command
        return result

    def undo(self) -> bool:
        """
        If possible, undo the command pointed by the undo/redo stack reader.
        Returns:
            True if undoing succeeded, False otherwise (or if there is nothing
            to be undone).
        """

        if not self.canUndo():
            return False

        result = self.__stack[(self.__stackPtr - 1) % __class__.__FIXED_STACK_CAPACITY].undo()
        self.__stackPtr  = self.__stackPtr - 1
        self.__stackBase = max(0, self.__stackPtr - __class__.__FIXED_STACK_CAPACITY)
        return result

    def redo(self) -> bool:
        """
        If possible, redo the command pointed by the undo/redo stack reader.
        Returns:
            True if redoing succeeded, False otherwise (or if there is nothing
            do be redone).
        """

        if not self.canRedo():
            return False

        self.__stackPtr  = self.__stackPtr  + 1
        self.__stackBase = self.__stackBase + 1
        result = self.__stack[(self.__stackPtr - 1) % __class__.__FIXED_STACK_CAPACITY].redo()
        return result

    def clearUndoRedoStack(self) -> None:
        """
        Clear the undo/redo stack.
        """

        self.__stack : List[EditorCommandBase] = []
        self.__stack.extend([__class__.__NopEditorCommand] * __class__.__FIXED_STACK_CAPACITY)
        self.__stackBase = self.__stackTop = self.__stackPtr = 0

    def canUndo(self) -> bool: return self.__stackBase <  self.__stackPtr
    def canRedo(self) -> bool: return self.__stackTop  >= self.__stackPtr
