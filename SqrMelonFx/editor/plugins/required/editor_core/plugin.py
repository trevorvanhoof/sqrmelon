import os
from pathlib import Path
import sys
from typing import ClassVar, Optional

from plugin_host_app import PluginBase, PluginContext
from qt import QMessageBox, QSettings


class WindowManagerMissingException(Exception): ...


class EditorCore(PluginBase):
    """
    Editor Core plugin.
    This is the foundational ground for every other plugin out there.
    """

    VERSION  : ClassVar[int] = 0x100 # Current version ID.
    DATA_PATH: ClassVar[str] = os.path.join(os.getenv('ProgramData', 'C:\\ProgramData') if os.name == 'nt' else Path('/usr/local/share'), "SqrMelonFx").replace('\\', '/')

    settings : QSettings     = None # Editor settings.
    context  : PluginContext = None # Plugin context.

    def pluginId(self) -> str: return "editorCore"
    def dependencies(self) -> list[str]: return []

    def loaded(self, context: PluginContext) -> None: 
        assert context is not None
        self.context = context
        if not PluginContext.gfx():
            raise WindowManagerMissingException()

    def unloaded(self) -> None:
        pass
#
    def activated(self, dependencies: dict[str, object], reloadContext: Optional[object] = None) -> None:

        # Install defaults.
        self.settings: QSettings = None
        try:
            if not os.path.isdir(EditorCore.DATA_PATH):
                os.makedirs(EditorCore.DATA_PATH)

            self.settings = QSettings(os.path.join(EditorCore.DATA_PATH, "SqrMelonFx.ini").replace('\\', '/'), QSettings.IniFormat)
            self.settings.setValue("version", EditorCore.VERSION)
            self.settings.setValue("editorInstallDir",  PluginContext.FileUtils.normalizedPath(Path(os.path.dirname(os.path.abspath(__file__))).__str__()))

            # Development defaults.
            if PluginContext.dev():
                if self.settings.value("lastOpenedProject" , None) is None:
                    self.settings.setValue("lastOpenedProject", PluginContext.FileUtils.normalizedPath(os.path.join(os.path.dirname(__file__), "default_project", "default_project.smx")))

        except Exception as e:
            # Installing defaults and reading settings is mandatory to operate.
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Critical)
            msgBox.setWindowTitle("Critical error")
            msgBox.setText("SqrMelon Fx couldn't be started.")
            msgBox.setInformativeText("An error occurred when installing required data to \"{}\". Check filesystem permissions and retry.".format(EditorCore.DATA_PATH))
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec()
            sys.exit(-1000)

        if PluginContext.dev():
            print("Editor core plugin activated.")
            print(f"Flags:{" dev" if PluginContext.dev() else ""} {" gfx" if PluginContext.gfx() else ""}.")
            print("Version ID: 0x{:04x}.".format(EditorCore.VERSION))
            print("User data path: \"{}\".".format(EditorCore.DATA_PATH))

        # Forward notifications to the console.
        self.context.notifyError.connect(self.__errorNotified)
        self.context.notifyWarning.connect(self.__warningNotified)
        self.context.notifyInformation.connect(self.__informationNotified)
        self.context.notifySuccess.connect(self.__successNotified)            

    def deactivated(self, isReloading: bool = False) -> Optional[object]: 

        # Disconnect console from notifications.
        self.context.notifyError.disconnect(self.__errorNotified)
        self.context.notifyWarning.disconnect(self.__warningNotified)
        self.context.notifyInformation.disconnect(self.__informationNotified)
        self.context.notifySuccess.disconnect(self.__successNotified)

    def __errorNotified      (self, context: PluginContext, message: str, payload: PluginContext.NotificationPayload) -> None: print(f"[ERR] {payload.title or "Error"      }: {message}{'\nDetails:\n' + payload.details if payload.details is not None and isinstance(payload.details, str) else ''}{'\nAdditional user data:\n' + payload.userdata if not None and isinstance(payload.userdata, str) else ''}")
    def __warningNotified    (self, context: PluginContext, message: str, payload: PluginContext.NotificationPayload) -> None: print(f"[WRN] {payload.title or "Warning"    }: {message}{'\nDetails:\n' + payload.details if payload.details is not None and isinstance(payload.details, str) else ''}{'\nAdditional user data:\n' + payload.userdata if not None and isinstance(payload.userdata, str) else ''}")
    def __informationNotified(self, context: PluginContext, message: str, payload: PluginContext.NotificationPayload) -> None: print(f"[INF] {payload.title or "Information"}: {message}{'\nDetails:\n' + payload.details if payload.details is not None and isinstance(payload.details, str) else ''}{'\nAdditional user data:\n' + payload.userdata if not None and isinstance(payload.userdata, str) else ''}")
    def __successNotified    (self, context: PluginContext, message: str, payload: PluginContext.NotificationPayload) -> None: print(f"[OK ] {payload.title or "Success"    }: {message}{'\nDetails:\n' + payload.details if payload.details is not None and isinstance(payload.details, str) else ''}{'\nAdditional user data:\n' + payload.userdata if not None and isinstance(payload.userdata, str) else ''}")
