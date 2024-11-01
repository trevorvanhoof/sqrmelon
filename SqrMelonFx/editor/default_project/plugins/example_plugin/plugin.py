from typing import Optional

from editor_core.plugin import EditorCore
from editor_core_ui.plugin import EditorCoreUi
from plugin_host_app import PluginBase


class DefaultProjectExamplePlugin(PluginBase):
    """
    Example plugin.
    """

    def pluginId(self) -> str: return "defaultProjectExamplePlugin"
    def dependencies(self) -> list[str]: return [ "editorCore", "editorCoreUi" ]
    def loaded  (self) -> None: pass
    def unloaded(self) -> None: pass
    def activated(self, dependencies: dict[str, object], reloadContext: Optional[object] = None) -> None:
        # Store dependencies locally.
        assert "editorCore"   in dependencies.keys()
        assert "editorCoreUi" in dependencies.keys()
        self.editorCore: EditorCore = dependencies["editorCore"]
        self.editorCoreUi: EditorCoreUi = dependencies["editorCoreUi"]
        print("[defaultProjectExamplePlugin] Hello, world!")

    def deactivated(self, isReloading: bool = False) -> Optional[object]: 
        # Free plugin dependencies.
        self.editorCoreUi = self.editorCore = None
        print("[defaultProjectExamplePlugin] Bye bye dear!")
