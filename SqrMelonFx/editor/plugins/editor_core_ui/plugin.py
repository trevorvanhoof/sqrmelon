import os
from typing import Optional

from qt import QCloseEvent, QMessageBox

from editor_core.plugin import EditorCore
from editor_core_ui.editor_window import EditorWindow
from editor_core_ui.style_manager import StyleManager
from editor_core_ui.toast_notification_manager import ToastNotificationManager
from plugin_host_app import PluginBase, PluginContext


class EditorCoreUi(PluginBase):
    """
    Editor Core UI plugin.
    This is the foundational ground for every other user interface out there.
    """

    editorCore  : EditorCore   = None
    editorWindow: EditorWindow = None
    styleManager: StyleManager = None

    def __init__(self) -> None:
        super().__init__()

    def pluginId(self) -> str: return "editorCoreUi"
    def dependencies(self) -> list[str]: return [ "editorCore" ]
    def loaded  (self) -> None: pass
    def unloaded(self) -> None: pass

    def activated(self, dependencies: dict[str, object], reloadContext: Optional[object] = None) -> None:

        # Store dependencies locally.
        assert "editorCore" in dependencies.keys()
        self.editorCore = dependencies["editorCore"]

        # Initialize.
        self.styleManager = StyleManager(PluginContext.normalizedPath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")), self.editorCore.settings.value("darkStyle", "true").__str__().lower() == "true")
        self.editorWindow = EditorWindow(self.styleManager, self.editorCore.settings, PluginContext.instance().cancellationToken)
        self.editorWindow.show()
        self.editorWindow.raise_()
        self.__toastNotificationManager = ToastNotificationManager(self.styleManager, self.editorWindow)

        # New plugins have to be added to the style manager.
        context: PluginContext = PluginContext.instance()
        context.pluginActivated  .connect(self.__pluginActivated  )
        context.pluginDeactivated.connect(self.__pluginDeactivated) 

        # Forward notifications to the toast notification manager.
        self.editorCore.notifyError      .connect(self.__errorNotified      )
        self.editorCore.notifyWarning    .connect(self.__warningNotified    )
        self.editorCore.notifyInformation.connect(self.__informationNotified)
        self.editorCore.notifySuccess    .connect(self.__successNotified    )

        # Update window title after project is open.
        self.editorCore.projectManager.projectLoaded.connect(self.__projectLoaded)
        self.editorWindow.beforeCloseEvent = self.__beforeCloseEvent
#
        if PluginContext.dev():
            print("Editor core UI plugin activated.")

    def deactivated(self, isReloading: bool = False) -> Optional[object]:

        # Disconnect connected signals.
        self.editorCore.projectManager.projectLoaded.disconnect(self.__projectLoaded)
        self.editorCore.notifyError      .disconnect(self.__errorNotified      )
        self.editorCore.notifyWarning    .disconnect(self.__warningNotified    )
        self.editorCore.notifyInformation.disconnect(self.__informationNotified)
        self.editorCore.notifySuccess    .disconnect(self.__successNotified    )

        context: PluginContext = PluginContext.instance()
        context.pluginActivated  .disconnect(self.__pluginActivated  )
        context.pluginDeactivated.disconnect(self.__pluginDeactivated)

        # Terminate.
        self.__toastNotificationManager = None
        self.editorCore.settings.setValue("darkStyle", self.styleManager.darkStyle)
        self.editorWindow.hide()
        self.editorWindow.destroy(True, True)
        self.editorWindow = self.styleManager = None

        # Free plugin dependencies.
        self.editorCore = None

    def __pluginActivated(self, plugin: PluginBase) -> None:
        """
        For plugins that contain resources, register the assets source to the style manager.
        Parameters:
            context (PluginContext): The plugin context that emitted the event.
            plugin (PluginBase): THe plugin that has been activated.
        """
        resourcesPath: str = PluginContext.normalizedPath(os.path.join(plugin.__module__, "resources"))
        if os.path.isdir(resourcesPath):
            self.styleManager.addSource(resourcesPath, plugin.pluginId())

    def __pluginDeactivated(self, plugin: PluginBase) -> None:
        """
        For plugins that contain resources, deregisters the assets source to the style manager.
        Parameters:
            context (PluginContext): The plugin context that emitted the event.
            plugin (PluginBase): THe plugin that has been deactivated.
        """
        resourcesPath: str = PluginContext.normalizedPath(os.path.join(plugin.__module__, "resources"))
        if os.path.isdir(resourcesPath):
            self.styleManager.removeSource(resourcesPath)

    def __errorNotified      (self, message: str, payload: EditorCore.NotificationPayload) -> None: self.__toastNotificationManager.displayErrorToastNotification      ((payload and payload.title) or "Error"      , message)
    def __warningNotified    (self, message: str, payload: EditorCore.NotificationPayload) -> None: self.__toastNotificationManager.displayWarningToastNotification    ((payload and payload.title) or "Warning"    , message)
    def __informationNotified(self, message: str, payload: EditorCore.NotificationPayload) -> None: self.__toastNotificationManager.displayInformationToastNotification((payload and payload.title) or "Information", message)
    def __successNotified    (self, message: str, payload: EditorCore.NotificationPayload) -> None: self.__toastNotificationManager.displaySuccessToastNotification    ((payload and payload.title) or "Success"    , message)
    def __projectLoaded      (self) -> None:
        self.editorWindow.setWindowTitle("SqrMelon Fx - {}{}".format(self.editorCore.projectManager.projectPath or self.editorCore.projectManager.projectName, 
            "*" if self.editorCore.projectManager.projectDirtyFlag else ""))

    def __beforeCloseEvent   (self, event: QCloseEvent) -> bool:
        if self.editorCore.projectManager.projectDirtyFlag:
            reply = QMessageBox.question(self, 'Unsaved changes',
                "Your project has unsaved local changes. Discard local changes, or save all to continue.",
            QMessageBox.SaveAll | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Cancel)

            # TODO dc QMessageBox.SaveAll must save the project.
            return reply in [ QMessageBox.SaveAll, QMessageBox.Discard ]
        else:
            return True
