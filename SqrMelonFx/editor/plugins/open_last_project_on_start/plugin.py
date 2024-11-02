import os
from typing import Optional

from editor_core.plugin import EditorCore
from editor_core_ui.plugin import EditorCoreUi
from plugin_host_app import PluginBase, PluginContext


class OpenLastProjectOnStart(PluginBase):
    """
    Try to re-open project from last session.
    """

    def pluginId(self) -> str: return "openLastProjectOnStart"
    def dependencies(self) -> list[str]: return [ "editorCore", "editorCoreUi" ]

    def loaded(self) -> None: pass

    def unloaded(self) -> None: pass

    def activated(self, dependencies: dict[str, object], reloadContext: Optional[object] = None) -> None:
        assert "editorCore"   in dependencies.keys()
        assert "editorCoreUi" in dependencies.keys()

        # Store dependencies locally.
        self.editorCore: EditorCore = dependencies["editorCore"]
        self.editorCoreUi: EditorCoreUi = dependencies["editorCoreUi"]
        PluginContext.instance().deferInvokeOnMainThread(self.__pluginHostLoaded)

    def deactivated(self, isReloading: bool = False) -> Optional[object]: 
        # Free plugin dependencies.
        self.editorCoreUi = self.editorCore = None

    def __pluginHostLoaded(self) -> None:
        """
        Try to re-open project from last session when the base host load sequence has completed.
        """
        lastOpenedProject: str = self.editorCore.settings.value("lastOpenedProject", None)
        if PluginContext.dev():
            print("Open last project on start feature enabled.")
        if lastOpenedProject is not None:
            if PluginContext.dev():
                print(f"Reopening \"{lastOpenedProject}\"...")
            self.editorCore.projectManager.openProject(lastOpenedProject)
            self.editorCore.done(f"Project \"{os.path.basename(lastOpenedProject)}\" loaded.", 
                EditorCore.NotificationPayload(title = "Session reopened", details = None, userdata = None))
