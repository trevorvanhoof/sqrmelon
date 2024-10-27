import os
from plugin_host_app import PluginBase, PluginContext

from typing import Optional

from editor_core.plugin import EditorCore
from editor_core_ui.editor_window import EditorWindow
from editor_core_ui.style_manager import StyleManager
from editor_core_ui.toast_notification_manager import ToastNotificationManager


class EditorCoreUi(PluginBase):
    """
    Editor Core UI plugin.
    This is the foundational ground for every other user interface out there.
    """

    styleManager: StyleManager = None
    editorWindow: EditorWindow = None

    def pluginId(self) -> str: return "editorCoreUi"
    def dependencies(self) -> list[str]: return [ "editorCore" ]

    def loaded(self, context: PluginContext) -> None: pass
    def unloaded(self) -> None: pass

    def activated(self, dependencies: dict[str, object], reloadContext: Optional[object] = None) -> None:

        # Store dependencies locally.
        assert "editorCore" in dependencies.keys()
        self.editorCore: EditorCore = dependencies["editorCore"]
        self.styleManager = StyleManager(PluginContext.FileUtils.normalizedPath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")), self.editorCore.settings.value("darkStyle", "true") == "true")
        self.editorWindow = EditorWindow(self.styleManager, self.editorCore.settings, self.editorCore.context.cancellationToken)
        self.editorWindow.show()
        self.editorWindow.raise_()
        self.__toastNotificationManager = ToastNotificationManager(self.styleManager, self.editorWindow)

        # New plugins have to be added to the style manager.
        self.editorCore.context.pluginActivated.connect(self.__pluginActivated)
        self.editorCore.context.pluginDeactivated.connect(self.__pluginDeactivated)

        # Forward notifications to the toast notification manager.
        self.editorCore.context.notifyError.connect(self.__errorNotified)
        self.editorCore.context.notifyWarning.connect(self.__warningNotified)
        self.editorCore.context.notifyInformation.connect(self.__informationNotified)
        self.editorCore.context.notifySuccess.connect(self.__successNotified)

        if PluginContext.dev():
            print("Editor core UI plugin activated.")

    def deactivated(self, isReloading: bool = False) -> Optional[object]:

        # Disconnect connected signals.
        self.editorCore.context.pluginActivated.disconnect(self.__pluginActivated)
        self.editorCore.context.pluginDeactivated.disconnect(self.__pluginDeactivated)

        # Disconnect toast notification manager from notifications.
        self.editorCore.context.notifyError.disconnect(self.__errorNotified)
        self.editorCore.context.notifyWarning.disconnect(self.__warningNotified)
        self.editorCore.context.notifyInformation.disconnect(self.__informationNotified)
        self.editorCore.context.notifySuccess.disconnect(self.__successNotified)

        # Free plugin dependencies.
        self.__toastNotificationManager = None
        self.editorCore.settings.setValue("darkStyle", self.styleManager.darkStyle)
        self.editorWindow.hide()
        self.editorWindow.destroy(True, True)
        self.editorWindow = self.styleManager = None
        self.editorCore = None

    def __pluginActivated(self, context: PluginContext, plugin: PluginBase) -> None:
        """
        For plugins that contain resources, register the assets source to the style manager.
        Parameters:
            context (PluginContext): The plugin context that emitted the event.
            plugin (PluginBase): THe plugin that has been activated.
        """
        if context != self.editorCore.context or self == plugin:
            return
        resourcesPath: str = PluginContext.FileUtils.normalizedPath(os.path.join(plugin.__module__, "resources"))
        if os.path.isdir(resourcesPath):
            self.styleManager.addSource(resourcesPath, plugin.pluginId())

    def __pluginDeactivated(self, context: PluginContext, plugin: PluginBase) -> None:
        """
        For plugins that contain resources, deregisters the assets source to the style manager.
        Parameters:
            context (PluginContext): The plugin context that emitted the event.
            plugin (PluginBase): THe plugin that has been deactivated.
        """
        if context != self.editorCore.context or self == plugin:
            return
        resourcesPath: str = PluginContext.FileUtils.normalizedPath(os.path.join(plugin.__module__, "resources"))
        if os.path.isdir(resourcesPath):
            self.styleManager.removeSource(resourcesPath)

    def __errorNotified      (self, context: PluginContext, message: str, payload: PluginContext.NotificationPayload) -> None: self.__toastNotificationManager.displayErrorToastNotification      (payload.title or "Error"      , message)
    def __warningNotified    (self, context: PluginContext, message: str, payload: PluginContext.NotificationPayload) -> None: self.__toastNotificationManager.displayWarningToastNotification    (payload.title or "Warning"    , message)
    def __informationNotified(self, context: PluginContext, message: str, payload: PluginContext.NotificationPayload) -> None: self.__toastNotificationManager.displayInformationToastNotification(payload.title or "Information", message)
    def __successNotified    (self, context: PluginContext, message: str, payload: PluginContext.NotificationPayload) -> None: self.__toastNotificationManager.displaySuccessToastNotification    (payload.title or "Success"    , message)
