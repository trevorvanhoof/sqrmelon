from abc import ABC, abstractmethod
import cProfile
from collections import namedtuple
import ctypes
import hashlib
import importlib
import inspect
import os
from pathlib import Path
import platform
import pstats
import subprocess
import sys
import tempfile
import threading
import time
from tkinter import Tk
import traceback
from typing import Any, Callable, ClassVar, Optional

import pyprof2calltree
import qdarktheme
from qt import QApplication, QCoreApplication, QMessageBox, QObject, QSurfaceFormat, Qt, Signal, Slot
from watchdog.observers import Observer
from watchdog.events import EVENT_TYPE_MOVED, FileSystemEvent, FileSystemEventHandler


class PluginContext(QApplication):
    """
    Plugin context interface.
    """
    atexit:             ClassVar[Signal] = Signal(object) # Signal(PluginContext). Emitted by plugin_host_app.py.
    mtimeEnabled:       ClassVar[bool]   = True # True if the filesystem supports mtime, false otherwise.
    _asyncExceptions:   ClassVar[list[Exception]] = [] # Uncaught exceptions coming from invokeOnMainThread().

    NotificationPayload = namedtuple("NotificationPayload", [ "title", "details", "userdata" ])

    notifyError      :  ClassVar[Signal] = Signal(object, str, Optional[NotificationPayload]) # Parameters = PluginContext, message, payload. 
    notifyWarning    :  ClassVar[Signal] = Signal(object, str, Optional[NotificationPayload]) # Parameters = PluginContext, message, payload.
    notifySuccess    :  ClassVar[Signal] = Signal(object, str, Optional[NotificationPayload]) # Parameters = PluginContext, message, payload.
    notifyInformation:  ClassVar[Signal] = Signal(object, str, Optional[NotificationPayload]) # Parameters = PluginContext, message, payload.

    # The following signals are emitted by plugin_host_app._PluginManager.
    pluginActivated:    ClassVar[Signal] = Signal(object, object) # Signal(PluginContext, PluginBase).
    pluginDeactivated:  ClassVar[Signal] = Signal(object, object) # Signal(PluginContext, Pluginbase).

    def __init__(self) -> None:
        super().__init__()
        self.cancellationToken = PluginContext.CancellationToken()

    def exec_(self) -> None:
        """
        Execute the application.
        Events are processed until requestExit() is called.
        At the end, functions connected to signal "atexit" are run.
        """
        
        # Run the Qt event loop.
        while not self.cancellationToken.cancellationRequested:
            self.processEvents()
            if len(self._asyncExceptions) > 0:
                e: Exception = self._asyncExceptions.pop(0)
                print("An exception occurred:", e)
                traceback.print_exception(type(e), e, e.__traceback__)
                raise e

        # Execute the atexit event chain.
        self.atexit.emit(self)

    def err (self, message: str, payload: Optional[NotificationPayload] = None) -> None: self.notifyError      .emit(self, message, payload)
    def warn(self, message: str, payload: Optional[NotificationPayload] = None) -> None: self.notifyWarning    .emit(self, message, payload)
    def done(self, message: str, payload: Optional[NotificationPayload] = None) -> None: self.notifySuccess    .emit(self, message, payload)
    def inf (self, message: str, payload: Optional[NotificationPayload] = None) -> None: self.notifyInformation.emit(self, message, payload)

    @staticmethod
    def dev() -> bool:
        """
        Determine whether we are running in a development or production environment.
        Returns:
            bool: True if we are running in a development environment, otherwise we are in a production environment.
        """
        return os.getenv("PYTHON_ENV") == "development"
    
    @staticmethod
    def gfx() -> bool:
        """
        Determine whether we are running in a graphics environment or not.
        Graphics environments are: Windows and Linux (with active DISPLAY) when "-ftext" command line argument is not present.
        Returns:
            bool: True if we are running in a graphics environment, False otherwise.
        """
        return "-ftext" not in sys.argv and (platform.system() == "Windows" or (platform.system() == "Linux" and "DISPLAY" in os.environ))

    class CancellationToken(object):
        """
        Cancellation token used to stop the event loop. 
        """
        __cancellationRequested: bool = False
        @property
        def cancellationRequested(self) -> bool: return self.__cancellationRequested
        def cancel(self) -> None: self.__cancellationRequested = True
  
    class __InvokeOnMainThread(QObject):
        """
        Invoke a method on the main thread.
        This is required to operate with the UI in Qt, among other things.
        """

        called = Signal()

        def __init__(self, exceptionsEnabled: bool, method: Callable, *args: Any, **kwargs: Any) -> None:
            """
            Invoke a method on the main thread.
            Parameters:
                exceptionsEnabled (bool): When true, exceptions are sent to be processed by the event loop.
                method (Callable): Method to invoke.
                args (Any): Positional arguments for the method.
                kwargs  (Any): Keyword arguments for the method.
            """
            super().__init__()
            self.moveToThread(QCoreApplication.instance().thread())
            self.setParent(QCoreApplication.instance())
            self.completed = False
            self.completedWithErrors = False
            self.exceptionsEnabled = exceptionsEnabled
            self.method = method
            self.args = args
            self.kwargs = kwargs
            self.called.connect(self.execute)
            self.called.emit()

        @Slot()
        def execute(self) -> None:
            try:
                self.method(*self.args, **self.kwargs)
            except Exception as e:
                self.completedWithErrors = True
                traceback.print_exception(e)
                if self.exceptionsEnabled:
                    PluginContext._asyncExceptions.append(e)
            self.setParent(None) # Trigger the GC.
            self.completed = True

    @staticmethod
    def invokeOnMainThread(method: Callable, *args: Any, **kwargs: Any) -> bool:
        """
        Invoke a method on the main thread.
        Parameters:
            method (Callable): Method to invoke.
            args (Any): Positional arguments for the method.
            kwargs  (Any): Keyword arguments for the method.
        Returns:
            bool: True for success; False otherwise.
        """
        invoker = PluginContext.__InvokeOnMainThread(True, method, *args, **kwargs)
        while not invoker.completed:
            time.sleep(0)
        return not invoker.completedWithErrors

    @staticmethod
    def invokeOnMainThreadWithExceptionsEnabled(exceptionsEnabled: bool, method: Callable, *args: Any, **kwargs: Any) -> bool:
        """
        Invoke a method on the main thread.
        Parameters:
            exceptionsEnabled (bool): When true, exceptions are sent to be processed by the event loop.
            method (Callable): Method to invoke.
            args (Any): Positional arguments for the method.
            kwargs  (Any): Keyword arguments for the method.
        Returns:
            bool: True for success; False otherwise.
        """
        invoker = PluginContext.__InvokeOnMainThread(exceptionsEnabled, method, *args, **kwargs)
        while not invoker.completed:
            time.sleep(0)
        return not invoker.completedWithErrors

    class FileUtils(object):
        """
        Static file utilities.
        """

        @staticmethod
        def normalizedPath(path: str) -> str:
            """
            Retrieve the canonical path after environment variables expansion.
            Parameters:
                path (str): Filesystem path to expand.
            Returns:
                str: Resulting path.
            """
            assert path is not None

            path = os.path.realpath(os.path.expandvars(path)) # Resolve env. variables, links and dots.
            # Request actual case from system, should only do something on Windows.
            return os.path.normpath(str(Path(path).resolve())).replace('\\', '/')


class PluginBase(ABC):
    """
    Abstract base class for plugins.
    This class defines the interface that all plugins must implement, including their identification, dependencies, and
    methods to manage their lifecycle.    
    """

    @abstractmethod
    def pluginId(self) -> str:
        """
        Get the unique identifier of the plugin.
        This identifier is used to:
            * Identify the plugin from other plugins (for example, when listing dependencies).
            * Namespace resources provided by this plugin in a similar fashion Python does (for example, to service a
              pixmap "foo/resources/bar.png" in plugin "foo", resource will be identified as "foo.bar").
        Returns:
            str: Unique identifier of the plugin.
        """
        pass

    @abstractmethod
    def dependencies(self) -> list[str]:
        """
        Get the list of dependencies for this plugin.
        Returns:
            list[str]: List of plugin identifiers required to activate this plugin.
        """
        pass

    @abstractmethod
    def loaded(self, context: PluginContext) -> None: 
        """
        Called when the plugin is loaded.
        It is guaranteed that this method will be called before activated().
        It is not guaranteed that dependencies will already be loaded by the time this method is called.
        It is not guaranteed that this method is called on the main thread. To ensure this, use PluginContext.invokeOnMainThread.
        Parameters:
            context (PluginContext): Context object for this editor instance.
        """
        pass

    @abstractmethod
    def unloaded(self) -> None: 
        """
        Called when the plugin is unloaded.
        It is guaranteed that this method will be called after deactivated().
        It is not guaranteed that dependencies will still be loaded by the time this method is called.
        It is not guaranteed that this method is called on the main thread. To ensure this, use PluginContext.invokeOnMainThread.
        """
        pass

    @abstractmethod
    def activated(self, dependencies: dict[str, object], reloadContext: Optional[object] = None) -> None: # type: ignore
        """
        Called when the plugin is activated.
        It is guaranteed that this method will be called after all dependencies have been loaded and loaded() has been
        called for all of them, and for this plugin.
        This method is guaranteed to be run in the main thread.
        Parameters:
            dependencies (dict[str, object]): Dictionary referencing all PluginBase objects that are dependency for this one.
            reloadContext (Optional[object]): During a reload operation, if deactivated() returned a reload context to
                carry data over between instances, this parameter represents that reload context.
        """
        pass

    @abstractmethod
    def deactivated(self, isReloading: bool = False) -> Optional[object]: 
        """
        Called when the plugin is deactivated.
        It is guaranteed that this method will be called before dependencies are deactivated.
        This method is guaranteed to be run in the main thread.
        Parameters:
            isReloading (bool): True if deactivation is due to a hot-reload operation, False otherwise.
        Returns:
            Optional[object]: Use this object when isReloading is True to carry over data to the next instance of this
            the plugin can carry over data to the next activation.
        """
        pass


class _PluginSourceIsNotDirectoryException     (Exception): ... # Plugin source is not a directory.
class _PluginSourceAlreadyExistsException      (Exception): ... # Plugin source already exists.
class _PluginBaseSubclassNotFoundException     (Exception): ... # Plugin does not declare a public class subclassing PluginBase.
class _PluginSourceCodeFileNotFoundException   (Exception): ... # No source code file "plugin.py" was found.
class _PluginIdAlreadyExistsException          (Exception): ... # Plugin ID already exists.
class _PluginDependencyCouldNotResolveException(Exception): ... # Plugin dependency couldn't be resolved (e.g., missing dependency or cyclic dependency).
class _PluginDefinitionMutatedException        (Exception): ... # Plugin definition (pluginId, dependencies) were changed during hot-reload operation.
class _PluginCouldNotBeRemovedException        (Exception): ... # Tried to remove a plugin marked as non-removable.


_PLUGIN_EXCLUDED_DIRS: list[str] = ['__pycache__']
_PLUGIN_EXCLUDED_EXTENSIONS: list[str] = [ '.py', '.pyw' ]


def _pluginModTime(path: str) -> float:
    """
    Find the most recent modification time of any file within the specified directory path, excluding certain 
    directories and files as specified by the user.

    Parameters:
        path (str): The plugin directory.
    Returns:
        float: The modification time (in seconds since the epoch) of the most recently modified file.
    """
    assert path is not None

    bestCandidate: float = 0
    for rootDir, directories, files in os.walk(path):
        directories[:] = [x for x in directories if x not in _PLUGIN_EXCLUDED_DIRS]
        for currFile in  [x for x in files if os.path.splitext(x)[1] in _PLUGIN_EXCLUDED_EXTENSIONS]:
            currFileLastModTime = os.path.getmtime(os.path.join(rootDir, currFile))
            if currFileLastModTime > bestCandidate:
                bestCandidate = currFileLastModTime
    return bestCandidate


def _pluginHashCode(path: str) -> str:
    """
    Compute a single MD5 hash for multiple files at once.
    Parameters:
        path (str): The plugin directory.
    Returns:
        str: MD5 hash representing the combined content of all given files.
    """
    assert path is not None

    md5Hash = hashlib.md5()
    for rootDir, directories, files in os.walk(path):
        directories[:] = [x for x in directories if x not in _PLUGIN_EXCLUDED_DIRS]
        for currFile in  [x for x in files if os.path.splitext(x)[1] in _PLUGIN_EXCLUDED_EXTENSIONS]:
            with open(os.path.join(rootDir, currFile), 'rb') as f:
                for dataChunk in iter(lambda: f.read(4096), b""):
                    md5Hash.update(dataChunk)
    return md5Hash.hexdigest()


class _PluginManager(QObject):
    """
    Manage the loading, unloading, and hot-reloading of plugins from specified sources.
    Notice that:
        * Changing plugin name and/or plugin dependencies requires a restart.
        * Adding or removing plugins have no effect,  and requires a restart.
    """

    def __init__(self, context: PluginContext, minimalPluginSources: list[str] = []) -> None:
        """
        Initialize the plugin manager instance.
        Parameters:
            context (PluginContext): The context representing the communication hub for plugins and the host.
            minimalPluginSources (list[str]): List of required plugin sources (not open for removal).
        """
        assert context is not None
        assert minimalPluginSources is not None

        super().__init__()

        self.__pluginManagerLock: threading.Lock = threading.Lock()
        self.__sources: dict[str, _PluginManager.__SourceChangeListener] = {}
        self.__instances: dict[str, tuple[_PluginManager.__PluginMetadata, PluginBase]] = {}
        self.__dependencyLine: list[str] = []

        self.__context = context
        for v in minimalPluginSources:
            self.addSource(v)
        for v in self.__instances.values():
            v[0].removable = False # Foundational plugins are not removable.
        self.__context.atexit.connect(self.__atexit)

    def addSource(self, source: str) -> int:
        """
        Add a new source directory for plugin discovery.
        The directory will be scanned for the available plugins, load them and activate them.
        Parameters:
            source (str): Directory to scan.
        Raises:
            _PluginSourceIsNotDirectoryException: the source is not a directory.
            _PluginSourceAlreadyExistsException: source was already added.
            _PluginDependencyCouldNotResolveException: plugin dependencies could not be solved (not found or cyclic).
        Returns:
            int: Number of plugins activated after the operation.
        """
        assert source is not None

        source = PluginContext.FileUtils.normalizedPath(source)
        if not os.path.isdir(source): raise _PluginSourceIsNotDirectoryException()
        if source in self.__sources : raise _PluginSourceAlreadyExistsException () # Load and instantiate all plugins in the directory.
        if source not in sys.path: sys.path.append(source)

        with self.__pluginManagerLock:

            pendingToResolve: list[tuple[_PluginManager.__PluginMetadata, PluginBase]] = []
            self.__sources[source] = _PluginManager.__SourceChangeListener()

            for d in os.listdir(source):
                if os.path.isfile(os.path.join(source, d)):
                    continue

                normalizedPluginPath = PluginContext.FileUtils.normalizedPath(os.path.join(source, d))
                instance: PluginBase =_PluginManager.__loadPlugin(normalizedPluginPath, False)
                if instance.pluginId() in self.__instances.keys() or any(thatInstance.pluginId() == instance.pluginId() for _, thatInstance in pendingToResolve):
                    raise _PluginIdAlreadyExistsException()

                instance.loaded(self.__context)
                instanceMetadata = _PluginManager.__PluginMetadata()
                instanceMetadata.pluginId   = instance.pluginId()
                instanceMetadata.removable  = True
                instanceMetadata.path       = PluginContext.FileUtils.normalizedPath(instance.__class__.__module__)
                instanceMetadata.source     = PluginContext.FileUtils.normalizedPath(os.path.dirname(instanceMetadata.path))
                instanceMetadata.modTime    = _pluginModTime (instanceMetadata.path)
                instanceMetadata.hashCode   = _pluginHashCode(instanceMetadata.path)
                pendingToResolve.append([instanceMetadata, instance])

            # Resolve plugin dependencies by brute-force.
            resolved: list[tuple[_PluginManager.__PluginMetadata, PluginBase]] = []
            while len(pendingToResolve) > 0:
                numPendingToResolve = len(pendingToResolve)
                for i in pendingToResolve:
                    dependencies = i[1].dependencies()
                    if len(dependencies) == 0: # Plugins without dependency are immediately resolved.
                        resolved.append(i)
                        pendingToResolve.remove(i)
                        continue

                    for j in reversed(dependencies):
                        if j in self.__instances or any(d[1].pluginId() == j for d in resolved):
                            dependencies[dependencies.index(j)] = None # Mark for deletion out of the loop.
                    dependencies = [x for x in dependencies if x is not None]
                    if len(dependencies) == 0:
                        resolved.append(i)
                        pendingToResolve.remove(i)
                        continue

                # No plugin could resolve in this round, hence we can't continue. Unload and raise the corresponding exception.
                if numPendingToResolve == len(pendingToResolve):
                    for i in resolved:
                        i[1].unloaded()
                    raise _PluginDependencyCouldNotResolveException()

            # Activate all plugins.
            for i in resolved:
                self.__instances[i[1].pluginId()] = i
                self.__addDependencyToDependencyLine(i[1].pluginId()) # Add plugin as self-dependency.
                dependencyInstances: list[PluginBase] = []
                for k in i[1].dependencies():
                    dependencyInstances.append(self.__instances[k][1])
                    self.__instances[k][0].dependents.append(i[1].pluginId())
                    self.__addDependencyToDependencyLine(k) # Update the dependency line.
                self.__context.invokeOnMainThread(lambda arg0 = i[1], arg1 = dependencyInstances: arg0.activated({instance.pluginId(): instance for instance in arg1}))
                self.__context.pluginActivated.emit(self.__context, i[1])

            # Observe the source directory.
            self.__sources[source].callback = self.__pluginChanged
            self.__sources[source].observer = Observer()
            self.__sources[source].observer.schedule(self.__sources[source], source, recursive = True)
            self.__sources[source].observer.start()
            return self.numActivatedPlugins

    def removeSource(self, source: str) -> int:
        """
        Remove a source directory registered via addSource(). That implies deactivating aand unloading all plugins
        within that directory.
        Source cannot be removed if any of the plugins in this source is referenced by any plugin in another source.
        Parameters:
            source (str): Directory to unload.
        Raises:
            _PluginDependencyCouldNotResolveException: Dependencies to other sources present.      
            _PluginCouldNotBeRemovedException: Tried to remove a plugin marked as not removable.
        Returns:
            int: Number of plugins activated after the operation.
        """
        assert source is not None

        source = PluginContext.FileUtils.normalizedPath(source)
        if source not in self.__sources:
            return self.numActivatedPlugins

        with self.__pluginManagerLock:

            # Ensure that no references to plugins in the source directory are held outside that specific source directory.
            pluginsToRemove : list[str] = []
            for k in self.__instances:
                if self.__instances[k][0].source == source:
                    for d in self.__instances[k][0].dependents:
                        if self.__instances[d][0].source != source:
                            raise _PluginDependencyCouldNotResolveException()
                    if not self.__instances[k][0].removable:
                        raise _PluginCouldNotBeRemovedException()
                    pluginsToRemove.append(k)

            removedPlugins: list[str] = []
            while len(pluginsToRemove) > 0:
                iterRemovedPlugins: list[str] = []
                for k in pluginsToRemove:
                    pluginPair = self.__instances[k]
                    if len(pluginPair[0].dependents) > 0:
                        continue
                    for q in pluginPair[1].dependencies():
                        if q in self.__instances:
                            self.__instances[q][0].dependents.remove(k)
                    iterRemovedPlugins.append(k)
                            
                for k in iterRemovedPlugins:
                    if k in pluginsToRemove:
                        pluginsToRemove.remove(k)
                removedPlugins = removedPlugins + iterRemovedPlugins

            # Stop listening filesystem changes.
            self.__sources[source].observer.stop()
            self.__sources[source].observer.join()

            # Deactivate and deregister all plugins in the source directory.
            for v in removedPlugins:
                self.__context.invokeOnMainThread(lambda arg0 = self.__instances[v][1]: arg0.deactivated())
                self.__context.pluginDeactivated.emit(self.__context, self.__instances[v][1])

            # Unload all plugins in the source directory.
            for v in removedPlugins:
                self.__instances[v][1].unloaded()
                self.__dependencyLine.remove(v)
                del self.__instances[v]

            del self.__sources[source]
            if source in sys.path: sys.path.remove(source)
            return self.numActivatedPlugins

    @property
    def numActivatedPlugins(self) -> int:
        return len(self.__instances)

    @staticmethod
    def __loadPlugin(pluginPath: str, reloading: bool = False) -> PluginBase:
        """
        Load the plugin declared in "plugin.py" at the given path. If a class named after the plugin directory name is
        found, it is instantiated. Otherwise, first class found that inherits from `PluginBase` is (be careful, global
        imports from other plugins are declaring imported clases before the actual loading plugin).
        Parameters:
            pluginPath (str): The path to the directory containing the `plugin.py` file.
            reloading (bool): True if this is part of hot-reload operation, False otherwise.
        Returns:
            PluginBase: An instance of the plugin class.
        Raises:
            _PluginSourceCodeFileNotFoundException: If the `plugin.py` file is not found.
            _PluginBaseSubclassNotFoundException: If no subclass of `PluginBase` is found in the `plugin.py` file.
        """
        assert pluginPath is not None

        if reloading:
            # When reloading, all source code files in the plugin need to be refreshed by invalidating the cache.
            # Otherwise, plugin files referenced by plugin.py do not update.
            pyFilesInPlugin = []
            for root, dirs, files in os.walk(pluginPath):
                if '__pycache__' in dirs: dirs.remove('__pycache__')
                for f in files:
                    if os.path.splitext(f)[1] in ['.py', '.pyw'] and f != '__init__.py':
                        pyFilesInPlugin.append(PluginContext.FileUtils.normalizedPath(os.path.join(root, f)))

            def moduleBasename(filePath: str):
                thisPath = os.path.abspath(filePath)
                while True:
                    if os.path.exists(os.path.join(thisPath, '__init__.py')): return os.path.basename(thisPath)
                    thatPath = os.path.dirname(thisPath)
                    if thatPath == thisPath: break
                    thisPath = thatPath
                return None
            
            pluginSourcePath = pluginPath.removesuffix(moduleBasename(pluginPath))
            for i in range(len(pyFilesInPlugin)):
                pyFilesInPlugin[i] = os.path.splitext(pyFilesInPlugin[i])[0].removeprefix(pluginSourcePath).replace('/', '.')
                if pyFilesInPlugin[i] in sys.modules:
                    del sys.modules[pyFilesInPlugin[i]]

        # Load the plugin.
        pluginFile = os.path.join(pluginPath, "plugin.py").replace('\\', '/')
        if not os.path.isfile(pluginFile):
            raise _PluginSourceCodeFileNotFoundException()

        pluginSpec   = importlib.util.spec_from_file_location(pluginPath, pluginFile)
        pluginModule = importlib.util.module_from_spec(pluginSpec)
        pluginSpec.loader.exec_module(pluginModule)

        pluginClass  = None
        for _, obj in inspect.getmembers(pluginModule, inspect.isclass):
            if issubclass(obj, PluginBase) and obj is not PluginBase and obj.__module__ == pluginModule.__name__:
                pluginClass = obj
                break

        if pluginClass is None:
            raise _PluginBaseSubclassNotFoundException()

        plugin = pluginClass()
        return plugin
    
    def __addDependencyToDependencyLine(self, dependency: str) -> None:
        """
        Add a dependency to the 1-dimensional dependency line.
        The line is sorted in dependency order from least to most. Duplicates are supported to perform some 
        reference counting.
        Parameters:
            dependency (str): Dependency to add.
        """
        assert dependency is not None
        if dependency in self.__dependencyLine:
            self.__dependencyLine.insert(self.__dependencyLine.index(dependency), dependency)
        else:
            self.__dependencyLine.append(dependency)

    def __pluginChanged(self, pluginPath: str) -> None:
        """
        If the plugin in the given path has changed, reload it.
        Reloading guarantees that the dependency chain is maintained (other plugins depending directly or indirectly)
        on the changed one will be deactivated, unloaded, loaded and re-activated in the right order.
        Parameters:
            pluginPath (str): Absolute path to the directory where the plugin is located.
        Raises:
            _PluginDefinitionMutatedException: Either pluginId or dependencies changed.
        """

        pluginId = next(key for key, (metadata, _) in self.__instances.items() if metadata.path == pluginPath)
        with self.__pluginManagerLock:

            pluginMetadata = self.__instances[pluginId][0]
            if PluginContext.mtimeEnabled:
                mtime = _pluginModTime(pluginPath)
                if mtime == pluginMetadata.modTime:
                    return # Discard if no changes were detected.
                pluginMetadata.modTime = mtime

            hashCode = _pluginHashCode(pluginPath)
            if hashCode == pluginMetadata.hashCode:
                return # Discard if no changes were detected. 
            pluginMetadata.hashCode = hashCode

            # Recover all dependencies affected by this plugin update.
            reloadChain: list[str] = []
            reloadChain.append(pluginId)
            idx: int = 0
            while idx < len(reloadChain):
                reloadChain += self.__instances[reloadChain[idx]][0].dependents
                idx += 1
            reloadChain = list(set([item for item in reloadChain if item != pluginId]))
            dependencyOrderMap = { value: index for index, value in enumerate(self.__dependencyLine) }
            reloadChain = sorted(reloadChain, key = lambda x: dependencyOrderMap[x])
            reloadChain.insert(0, pluginId)

            # Save non-reloadable data.
            baseInfo: list[tuple[str, str, list[str]]] = [] # Name, classname, dependency list.
            for i in reloadChain:
                baseInfo.append([i, self.__instances[i][1].__class__.__name__, self.__instances[i][1].dependencies()])

            # Deactivate and unload the dependency chain.
            reloadContextes: list[Optional[object]] = []
            for i in reversed(reloadChain):
                self.__context.invokeOnMainThread(lambda arg0 = reloadContextes, arg1 = self.__instances[i][1]: arg0.append(arg1.deactivated(True)))
                self.__context.pluginDeactivated.emit(self.__context, self.__instances[i][1])

            for i in reversed(reloadChain):
                self.__instances[i][1].unloaded() # We do not deinstantiate the plugin to ensure we can fall back to the previous version.

            # Load and re-activate the dependency chain.
            reloadedInstances: list[PluginBase] = []
            reloadContextes.reverse()
#            try:
            for a, b in zip(reloadChain, baseInfo):
                instance = _PluginManager.__loadPlugin(self.__instances[a][0].path, True)
                if instance.pluginId() != b[0] or instance.__class__.__name__ != b[1] or instance.dependencies() != b[2]:
                    raise _PluginDefinitionMutatedException()
                reloadedInstances.append(instance)
            for i in reloadedInstances:
                i.loaded(self.__context)

            for a, b in zip(reloadedInstances, reloadContextes):
                dependencyInstances: list[PluginBase] = []
                for k in a.dependencies():
                    dependencyInstances.append(
                        next((w for w in reloadedInstances + [inst for _, (_, inst) in self.__instances.items()] if w.pluginId() == k), None)
                    )
                result = self.__context.invokeOnMainThreadWithExceptionsEnabled("--silent-plugin-exc" not in sys.argv, lambda arg0 = a, arg1 = dependencyInstances, arg2 = b: arg0.activated({instance.pluginId(): instance for instance in arg1}, arg2))
                if result:
                    self.__context.pluginActivated.emit(self.__context, a)
                else:
                    print("Plugin contains errors. Falling back to previous state...")

                    reloadedInstances = [] # Do not replace loaded instances.
                    for a, b in zip(reloadChain, reloadContextes):
                        self.__instances[a][1].loaded(self.__context)
                        dependencyInstances: list[PluginBase] = []
                        for k in self.__instances[a][1].dependencies():
                            dependencyInstances.append(self.__instances[k][1])
                        self.__context.invokeOnMainThread(lambda arg0 = self.__instances[a][1], arg1 = dependencyInstances, arg2 = b: arg0.activated({instance.pluginId(): instance for instance in arg1}, arg2))
                        self.__context.pluginActivated.emit(self.__context, self.__instances[a][1])

            for i in reloadedInstances:
                self.__instances[i.pluginId()][1] = i

    def __atexit(self) -> None:
        """
        Remove all sources.
        """
        
        for v in self.__instances.values():
            v[0].removable = True
        sourceStack = list(reversed(self.__sources.keys()))
        for k in sourceStack:
            self.removeSource(k)


    class __SourceChangeListener(FileSystemEventHandler):
        """
        Filesystem observer for plugin code.
        Emits events for each file added, moved and deleted in the corresponding plugin folder.
        Files under directory "__pycache__" are ignored.
        """
        observer: Observer      = None  # type: ignore
        callback: Callable[[str], None] = None # Callback run when a file is changed.

        def on_any_event(self, event: FileSystemEvent) -> None:
            """
            Catch-all event handler.
            Parameters:
                event (FileSystemEvent): The event object representing the file system event.
            """
            assert self.callback is not None

            npath = PluginContext.FileUtils.normalizedPath(event.src_path if event.event_type is not EVENT_TYPE_MOVED else event.dest_path)
            if event.is_directory or os.path.isdir(npath):
                return
            dpath = os.path.dirname(npath)
            if dpath.endswith('/__pycache__') or '/__pycache__/' in dpath: return
            if os.path.splitext(npath)[1] not in [ ".py", ".pyw" ]: return
            self.callback(dpath)


    class __PluginMetadata(object):
        """
        Plugin metadata.
        """

        pluginId    : str       = None  # Unique identifier to name this plugin across the plugin ecosystem.
        path        : str       = None  # Absolute path to the directory where this plugin is located.
        removable   : bool      = False # Whether this plugin can be removed (=True) or not (=False).
        source      : str       = None  # Absolute path to the source directory where this plugin was found.
        modTime     : float     = -1    # Last modification time of all relevant files in this plugin.
        hashCode    : str       = None  # Global hashcode of all relevant files in this plugin.
        dependents  : list[str] = None    # List of plugins that depend on this plugin (for hot-reloading purposes).

        def __init__(self) -> None:
            self.dependents     = []


def _runPluginHostApp() -> None:
    """
    Run the application.
    If environment variable PYTHON_ENV == "development", the application is 
    run as development build.
    Raises:
        WindowManagerNotFoundException: Program is run in a terminal with no access to graphical environment.
    """

    if PluginContext.gfx():
        # We found that not setting a version in Ubuntu didn't work.
        glFormat = QSurfaceFormat()
        glFormat.setVersion(4, 1)
        glFormat.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        glFormat.setDefaultFormat(glFormat)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
        qdarktheme.enable_hi_dpi()

    appExitCode = None
    try:
        pluginSources: list[str] = []
        for i in sys.argv:
            if i.startswith('-p'):
                pluginSources.append(PluginContext.FileUtils.normalizedPath(i[2:]).strip('"\''))

        if PluginContext.gfx() and os.name == 'nt':
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('trevorvanhoof.sqrmelonfx')

        # Execute the application.
        pluginContext = PluginContext()
        pluginManager =_PluginManager(pluginContext, pluginSources)
        if pluginManager.numActivatedPlugins > 0:
            pluginContext.exec_()
        else:
            raise Exception(f"ERROR: No plugins found in {pluginSources.__str__()}. Specify one or more plugin sources with argument \"-p<PLUGIN_SOURCE_PATH>\".")

    except Exception as e:
        if not PluginContext.dev():
            if PluginContext.gfx():
                msgBox = QMessageBox()
                msgBox.setIcon(QMessageBox.Critical)
                msgBox.setWindowTitle("Critical error")
                msgBox.setText("Unhandled exception found running SqrMelon Fx:")
                msgBox.setInformativeText(traceback.format_exc())
                msgBox.setStandardButtons(QMessageBox.Ok)
                msgBox.exec()
            else:
                print("ERROR: Unhandled exception found running SqrMelon Fx:\n{traceback.format_exc()}")
            appExitCode = -1000
        else:
           raise e

    sys.exit(appExitCode)


if __name__ == '__main__':

    # Alias __main__ as plugin_host_app to fix PluginBase inheritance. 
    sys.modules["plugin_host_app"] = sys.modules["__main__"]

    if "--qcachegrind" in sys.argv:
        # Profile to file and eventually launch qcachegrind.exe if present in the application filesystem.
        autoDiscoveredCacheGrind: str = None
        for f in Path(os.path.join(os.path.dirname(__file__), "..", "..")).rglob("qcachegrind.exe"):
            autoDiscoveredCacheGrind = f.__str__()
            break

        profileReportFn = tempfile.mktemp()
        print(f"Profiling to \"{profileReportFn}\"...")
        cProfile.runctx("_runPluginHostApp()", globals(), locals(), filename = profileReportFn)
        pyprof2calltree.convert(pstats.Stats(profileReportFn), profileReportFn)

        if autoDiscoveredCacheGrind is not None:
            subprocess.run([autoDiscoveredCacheGrind, profileReportFn])

        cb = Tk()
        cb.withdraw()
        cb.clipboard_clear()
        cb.clipboard_append(PluginContext.FileUtils.normalizedPath(profileReportFn))
        cb.update()
        print("Path to the profiling report file has been copied to the clipboard.")

    else:
        _runPluginHostApp()
