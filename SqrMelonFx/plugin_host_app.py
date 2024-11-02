from abc import abstractmethod
import cProfile
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
    pluginActivated     : ClassVar[Signal] = Signal(object) # Signal(PluginBase).
    pluginDeactivated   : ClassVar[Signal] = Signal(object) # Signal(PluginBase).
    mtimeEnabled        : ClassVar[bool]   = True # True if the filesystem supports mtime, false otherwise.
    atexit              : ClassVar[Signal] = Signal() # Signal().

    def __init__(self, pluginSources: list[str]) -> None:
        """
        """
        assert pluginSources is not None

        super().__init__()
        self.cancellationToken = PluginContext.CancellationToken()
        self.__deferredCallbacks: list[Callable] = []

        self.__pluginManager   = PluginContext.__PluginManager(pluginSources)
        if self.__pluginManager.numActivatedPlugins == 0:
            raise Exception(f"ERROR: No plugins found in {pluginSources.__str__()}. Specify one or more plugin sources with argument \"-p<PLUGIN_SOURCE_PATH>\".")
        self.__pluginManager.pluginActivated  .connect(lambda path: self.pluginActivated  .emit(path))
        self.__pluginManager.pluginDeactivated.connect(lambda path: self.pluginDeactivated.emit(path))

    def exec_(self) -> None:
        """
        Execute the application.
        Events are processed until requestExit() is called.
        At the end, functions connected to signal "atexit" are run.
        """
        # Run the Qt event loop.
        while not self.cancellationToken.cancellationRequested:
            self.processEvents()
            while len(self.__deferredCallbacks) > 0:
                self.__deferredCallbacks.pop(0)()

        # Execute the atexit event chain.
        self.atexit.emit()

    def addPluginSource   (self, source: str) -> int: return self.__pluginManager.addSource   (source)
    def removePluginSource(self, source: str) -> int: return self.__pluginManager.removeSource(source)

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

    def deferInvokeOnMainThread(self, method: Callable, *args: Any, **kwargs: Any) -> None:
        """
        Invoke a method on the main thread as soon as possible.
        For immediate execution, use invokeOnMainThread() instead.
        Parameters:
            method (Callable): Method to invoke.
            args (Any): Positional arguments for the method.
            kwargs  (Any): Keyword arguments for the method.
        """
        self.__deferredCallbacks.append(lambda: method(*args, **kwargs))

    @staticmethod
    def invokeOnMainThread(method: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Invoke a method on the main thread immediately.
        Consider using deferInvokeOnMainThread if you do not need immediate invocation.
        Parameters:
            method (Callable): Method to invoke.
            args (Any): Positional arguments for the method.
            kwargs  (Any): Keyword arguments for the method.
        Returns:
            Any: If type is list[Exception], exception(s) raised during invocation are listed here; otherwise the value
                returned by the invoked function.
        """

        class __InvokeOnMainThread(QObject):
            """
            Invoke a method on the main thread.
            This is required to operate with the UI in Qt, among other things.
            """
            called = Signal()
            exceptions: list[Exception] = None

            def __init__(self, method: Callable, *args: Any, **kwargs: Any) -> None:
                """
                Invoke a method on the main thread.
                Parameters:
                    args (Any): Positional arguments for the method.
                    kwargs  (Any): Keyword arguments for the method.
                """
                super().__init__()

                self.moveToThread(QCoreApplication.instance().thread())
                self.setParent(QCoreApplication.instance())
                self.completed  = False
                self.completedWithErrors = False
                self.exceptions = []
                self.result = None
                self.method = method
                self.args = args
                self.kwargs = kwargs
                self.called.connect(self.execute)
                self.called.emit()

            @Slot()
            def execute(self) -> None:
                try:
                    self.result = self.method(*self.args, **self.kwargs)
                except Exception as e:
                    self.completedWithErrors = True
                    traceback.print_exception(e)
                    self.exceptions.append(e)
                self.setParent(None) # Trigger the GC.
                self.completed = True

        invoker = __InvokeOnMainThread(method, *args, **kwargs)
        while not invoker.completed:
            time.sleep(0)
        return invoker.exceptions if invoker.completedWithErrors else invoker.result


    class __DirectoryWatcher(FileSystemEventHandler):
        """
        Monitor directory changes.
        """

        def __init__(self, path: str, changed: Callable[[str], None], excludedDirs: list[str], extFilter: Optional[list[str]] = None) -> None:
            """
            Initialize monitoring the given directory.
            Monitoring occurs in a recursive manner. All directories but those in excludeDirs are evaluated.
            Parameters:
                path (str): Path to the directory to monitor.
                changed (Callable[[str], None]): Callback to run when a change is detected.
                excludedDirs (list[str]): List of directories to exclude (directory names).
                extFilter (optional[list[str]]): If not None, list of file extensions to monitor.
            """
            assert path is not None
            assert os.path.isdir(path)
            assert changed is not None
            assert excludedDirs is not None
            assert extFilter is not None

            super().__init__()

            self.path        : str       = PluginContext.normalizedPath(path)
            self.changed     : Callable[[str], None] = changed
            self.observer    : Observer  = Observer() # type: ignore
            self.refCount    : int       = 0
            self.paused      : int       = 0
            self.excludedDirs: list[str] = excludedDirs
            self.extFilter   : list[str] = extFilter
            self.mtime       : float     = self.__mtime   (self.path, self.excludedDirs, self.extFilter)
            self.hashCode    : str       = self.__hashCode(self.path, self.excludedDirs, self.extFilter)

            self.observer.schedule(self, self.path, recursive = True)
            self.observer.start()

        def __del__(self):
            """
            Terminate monitoring.
            """
            self.observer.stop()
            self.observer.join()

        def on_any_event(self, event: FileSystemEvent) -> None:
            """
            Change event handler.
            Runs the "changed" callback provided in construction-time if the following conditions are honored:
                * The changed path is not a directory.
                * The changed path is not a excluded directory.
                * If the extension filter was provided, the file extension is in the filter.
                * The contents of the changed file have been altered.
            event (FileSystemEvent): Event data (exact type depends on event type).
            """

            path = PluginContext.normalizedPath(event.src_path if event.event_type != EVENT_TYPE_MOVED else event.dest_path)
            if os.path.isdir(path):
                return # Discard, monitoring is on files and not directories.

            if PluginContext.mtimeEnabled:
                mtime: float = self.__mtime(self.path, self.excludedDirs, self.extFilter)
                if event.event_type == EVENT_TYPE_MOVED and mtime  == self.mtime:
                    return # Discard if no changes were detected.
                self.mtime = mtime

            hashCode: str = self.__hashCode(self.path, self.excludedDirs, self.extFilter)
            if event.event_type == EVENT_TYPE_MOVED and hashCode  == self.hashCode:
                return # Discard if no changes were detected.
            self.hashCode = hashCode
            
            if self.paused < 1:
                if any(part not in self.excludedDirs for part in Path(path).parts) and (os.path.splitext(path)[1] in self.extFilter if self.extFilter else True):
                    if PluginContext.dev():
                        print(f"File modification detected: \"{path}\".")
                    self.changed(path)

        @staticmethod
        def __mtime(path: str, excludedDirs: list[str] = [], extFilter: Optional[list[str]] = None) -> float:
            """
            If "path" points to a file, find the modification time of the file. If "path" points to a directory, find
            the most recent modification time of any file within it according to the provided criteria.
            Parameters:
                path (str): Path to the file or directory to evaluate.
                excludedDirs (list[str]): If "path" points to a directory, list of directory names to exclude.
                extFilter (list[str]): If "path" points to a directory, list of file extensions to include.
                    Set to None to include all file extensions.
            Returns:
                float: The modification time (in seconds since the epoch) of the most recently modified file.
            """
            assert path is not None
            assert excludedDirs is not None

            path = PluginContext.normalizedPath(path)
            if os.path.isfile(path):
                return os.path.getmtime(path)

            bestCandidate: float = 0
            for rootDir, directories, files in os.walk(path):
                directories[:] = [x for x in directories if x not in excludedDirs]
                for currFile in  [x for x in files if os.path.splitext(x)[1] in extFilter] if extFilter else files:
                    currFileLastModTime = os.path.getmtime(os.path.join(rootDir, currFile))
                    if currFileLastModTime > bestCandidate:
                        bestCandidate = currFileLastModTime
            return bestCandidate

        @staticmethod
        def __hashCode(path: str, excludedDirs: list[str] = [], extFilter: Optional[list[str]] = None) -> str:
            """
            If "path" points to a file, find the MD5 hash code for such file. If "path" points to a directory, find
            the MD5 hash code of any file within it according to the provided criteria.
            Compute a single MD5 hash for multiple files at once.
            Parameters:
                path (str): Path to the file or directory to evaluate.
                excludedDirs (list[str]): If "path" points to a directory, list of directory names to exclude.
                extFilter (list[str]): If "path" points to a directory, list of file extensions to include.
                    Set to None to include all file extensions.
            Returns:
                str: MD5 hash representing the combined content of all given files.
            """
            assert path is not None
            assert excludedDirs is not None

            path = PluginContext.normalizedPath(path)
            allFiles: list[str] = []
            if os.path.isfile(path):
                allFiles.append(path)
            else:
                for rootDir, directories, files in os.walk(path):
                    directories[:] = [x for x in directories if x not in excludedDirs]
                    for currFile in  [x for x in files if os.path.splitext(x)[1] in extFilter]:
                        allFiles.append(PluginContext.normalizedPath(os.path.join(rootDir, currFile)))

            md5Hash = hashlib.md5()
            for i in allFiles:
                with open(i, 'rb') as f:
                    for dataChunk in iter(lambda: f.read(4096), b""):
                        md5Hash.update(dataChunk)
            return md5Hash.hexdigest()

    __directoryWatchers: dict[str, __DirectoryWatcher] = {}

    def watchDirectory(self, path: str, changed: Callable[[str], None], excludedDirs: list[str] = [], extFilter: Optional[list[str]] = None) -> None:
        """
        Start monitoring filesystem changes for the given directory.
        Directory monitoring is ref-counted (watching the directory twice requires unwatching it twice).
        Parameters:
            path (str): Path to the directory to monitor.
            changed (Callable[[str], None]): Callback to run when a change is detected.
            excludedDirs (list[str]): List of directories to exclude (directory names).
            extFilter (optional[list[str]]): If not None, list of file extensions to monitor.
        """
        assert path is not None
        assert changed is not None
        assert excludedDirs is not None

        path = PluginContext.normalizedPath(path)
        if path not in self.__directoryWatchers:
            self.__directoryWatchers[path] = PluginContext.__DirectoryWatcher(path, changed, excludedDirs, extFilter or [])
        self.__directoryWatchers[path].refCount += 1

    def unwatchDirectory(self, path: str) -> None:
        """
        Stops monitoring filesystem changes for the given directory.
        Directory monitoring is ref-counted (watching the directory twice requires unwatching twice).
        Parameters:
            path (str): Path to the directory to monitor.
        """
        assert path is not None

        path = PluginContext.normalizedPath(path)
        if path in self.__directoryWatchers:
            self.__directoryWatchers[path].refCount -= 1
            if  self.__directoryWatchers[path].refCount == 0:
                self.__directoryWatchers[path].__del__()
                del self.__directoryWatchers[path]
        else:
            raise Exception()

    def setWatchDirectoryPauseFlag(self, path: str, paused: bool) -> None:
        """
        Pause or unpause monitoring of the directory.
        Pause is ref-counted (pausing monitoring twice requires unpausing twice).
        Parameters:
            path (str): Path to the directory to monitor.
        """
        assert path is not None

        path = PluginContext.normalizedPath(path)
        if path in self.__direectoryWatchers:
            self.__directoryWatchers[path].paused += 1 if paused else -1
        else:
            raise Exception()

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

        path = os.path.realpath( os.path.expandvars(path)) # Resolve env. variables, links and dots.
        # Request actual case from system, should only do something on Windows.
        return os.path.normpath(str(Path(path).resolve())).replace('\\', '/')

    
    class PluginSourceIsNotDirectoryException     (Exception): ... # Plugin source is not a directory.
    class PluginSourceAlreadyExistsException      (Exception): ... # Plugin source already exists.
    class PluginBaseSubclassNotFoundException     (Exception): ... # Plugin does not declare a public class subclassing PluginBase.
    class PluginSourceCodeFileNotFoundException   (Exception): ... # No source code file "plugin.py" was found.
    class PluginIdAlreadyExistsException          (Exception): ... # Plugin ID already exists.
    class PluginDependencyCouldNotResolveException(Exception): ... # Plugin dependency couldn't be resolved (e.g., missing dependency or cyclic dependency).
    class PluginDefinitionMutatedException        (Exception): ... # Plugin definition (pluginId, dependencies) were changed during hot-reload operation.
    class PluginCouldNotBeRemovedException        (Exception): ... # Tried to remove a plugin marked as non-removable.


    _PLUGIN_EXCLUDED_DIRS: list[str] = ['__pycache__']
    _PLUGIN_INCLUDED_EXTENSIONS: list[str] = [ '.py', '.pyw' ]


    class __PluginManager(QObject):
        """
        Manage the loading, unloading, and hot-reloading of plugins from specified sources.
        Notice that:
            * Changing plugin name and/or plugin dependencies requires a restart.
            * Adding or removing plugins have no effect,  and requires a restart.
        """
        pluginActivated     : ClassVar[Signal] = Signal(object) # Signal(PluginBase).
        pluginDeactivated   : ClassVar[Signal] = Signal(object) # Signal(Pluginbase).

        def __init__(self, minimalPluginSources: list[str] = []) -> None:
            """
            Initialize the plugin manager instance.
            Parameters:
                minimalPluginSources (list[str]): List of required plugin sources (not open for removal).
            """
            assert minimalPluginSources is not None

            super().__init__()
            self.__pluginManagerLock: threading.Lock = threading.Lock()
            self.__sources  : list[str] = []
            self.__instances: dict[str, tuple[PluginContext.__PluginManager.__PluginMetadata, PluginBase]] = {}
            self.__dependencyLine: list[str] = []

            for v in minimalPluginSources:
                self.addSource(v)
            for v in self.__instances.values():
                v[0].removable = False # Foundational plugins are not removable.
            PluginContext.instance().atexit.connect(self.__atexit)

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

            source = PluginContext.normalizedPath(source)
            if not os.path.isdir(source): raise PluginContext.PluginSourceIsNotDirectoryException()
            if source in self.__sources : raise PluginContext.PluginSourceAlreadyExistsException () # Load and instantiate all plugins in the directory.
            if source not in sys.path: sys.path.append(source)

            with self.__pluginManagerLock:

                pendingToResolve: list[tuple[PluginContext.__PluginManager.__PluginMetadata, PluginBase]] = []
                for d in os.listdir(source):
                    if os.path.isfile(os.path.join(source, d)):
                        continue

                    normalizedPluginPath = PluginContext.normalizedPath(os.path.join(source, d))
                    instance: PluginBase = self.__loadPlugin(normalizedPluginPath, False)
                    if instance.pluginId() in self.__instances.keys() or any(thatInstance.pluginId() == instance.pluginId() for _, thatInstance in pendingToResolve):
                        raise PluginContext.PluginIdAlreadyExistsException()

                    instance.loaded()
                    instanceMetadata = self.__PluginMetadata()
                    instanceMetadata.pluginId   = instance.pluginId()
                    instanceMetadata.removable  = True
                    instanceMetadata.path       = PluginContext.normalizedPath(instance.__class__.__module__)
                    instanceMetadata.source     = PluginContext.normalizedPath(os.path.dirname(instanceMetadata.path))
                    pendingToResolve.append([instanceMetadata, instance])

                # Resolve plugin dependencies by brute-force.
                resolved: list[tuple[PluginContext.__PluginManager.__PluginMetadata, PluginBase]] = []
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
                        raise PluginContext.PluginDependencyCouldNotResolveException()

                # Activate all plugins.
                context: PluginContext = PluginContext.instance()
                for i in resolved:
                    self.__instances[i[1].pluginId()] = i
                    self.__addDependencyToDependencyLine(i[1].pluginId()) # Add plugin as self-dependency.
                    dependencyInstances: list[PluginBase] = []
                    for k in i[1].dependencies():
                        dependencyInstances.append(self.__instances[k][1])
                        self.__instances[k][0].dependents.append(i[1].pluginId())
                        self.__addDependencyToDependencyLine(k) # Update the dependency line.
                    result = context.invokeOnMainThread(lambda arg0 = i[1], arg1 = dependencyInstances: arg0.activated({instance.pluginId(): instance for instance in arg1}))
                    for i in result if isinstance(result, list) else []:
                        raise i
                    self.pluginActivated.emit(i[1])

                # Observe the source directory.
                if not "--no-hotreload" in sys.argv:
                    context.watchDirectory(source, self.__pluginChanged, PluginContext._PLUGIN_EXCLUDED_DIRS, PluginContext._PLUGIN_INCLUDED_EXTENSIONS)
            self.__sources.append(source)
            return self.numActivatedPlugins

        def removeSource(self, source: str) -> int:
            """
            Remove a source directory registered via addSource(). That implies deactivating aand unloading all plugins
            within that directory.
            Source cannot be removed if any of the plugins in this source is referenced by any plugin in another source.
            Parameters:
                source (str): Directory to unload.
            Raises:
                PluginDependencyCouldNotResolveException: Dependencies to other sources present.      
                PluginCouldNotBeRemovedException: Tried to remove a plugin marked as not removable.
            Returns:
                int: Number of plugins activated after the operation.
            """
            assert source is not None

            source = PluginContext.normalizedPath(source)
            if source not in self.__sources:
                return self.numActivatedPlugins

            with self.__pluginManagerLock:

                # Ensure that no references to plugins in the source directory are held outside that specific source directory.
                pluginsToRemove : list[str] = []
                for k in self.__instances:
                    if self.__instances[k][0].source == source:
                        for d in self.__instances[k][0].dependents:
                            if self.__instances[d][0].source != source:
                                raise PluginContext.PluginDependencyCouldNotResolveException()
                        if not self.__instances[k][0].removable:
                            raise PluginContext.PluginCouldNotBeRemovedException()
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
                context: PluginContext = PluginContext.instance()
                if not "--no-hotreload" in sys.argv:
                    context.unwatchDirectory(source)

                # Deactivate and deregister all plugins in the source directory.
                for v in removedPlugins:
                    context.instance().invokeOnMainThread(lambda arg0 = self.__instances[v][1]: arg0.deactivated())
                    context.instance().pluginDeactivated.emit(self.__instances[v][1])

                # Unload all plugins in the source directory.
                for v in removedPlugins:
                    self.__instances[v][1].unloaded()
                    self.__dependencyLine.remove(v)
                    del self.__instances[v]

                self.__sources.remove(source)
                if source in sys.path: sys.path.remove(source)
                return self.numActivatedPlugins

        @property
        def numActivatedPlugins(self) -> int:
            return len(self.__instances)

        @staticmethod
        def __loadPlugin(pluginPath: str, reloading: bool = False) -> object:
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
                PluginSourceCodeFileNotFoundException: If the `plugin.py` file is not found.
                PluginBaseSubclassNotFoundException: If no subclass of `PluginBase` is found in the `plugin.py` file.
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
                            pyFilesInPlugin.append(PluginContext.normalizedPath(os.path.join(root, f)))

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
                raise PluginContext.PluginSourceCodeFileNotFoundException()

            pluginSpec   = importlib.util.spec_from_file_location(pluginPath, pluginFile)
            pluginModule = importlib.util.module_from_spec(pluginSpec)
            pluginSpec.loader.exec_module(pluginModule)

            pluginClass  = None
            for _, obj in inspect.getmembers(pluginModule, inspect.isclass):
                if issubclass(obj, PluginBase) and obj is not PluginBase and obj.__module__ == pluginModule.__name__:
                    pluginClass = obj
                    break

            if pluginClass is None:
                raise PluginContext.PluginBaseSubclassNotFoundException()

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
                pluginPath (str): Absolute path to the file changed.
            Raises:
                PluginDefinitionMutatedException: Either pluginId or dependencies changed.
            """

            pluginPath = os.path.dirname(pluginPath) if os.path.isfile(pluginPath) else pluginPath
            pluginId = next(key for key, (metadata, _) in self.__instances.items() if metadata.path == pluginPath)
            with self.__pluginManagerLock:

                pluginMetadata = self.__instances[pluginId][0]

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
                context: PluginContext = PluginContext.instance()
                reloadContextes: list[Optional[object]] = []
                for i in reversed(reloadChain):
                    context.invokeOnMainThread(lambda arg0 = reloadContextes, arg1 = self.__instances[i][1]: arg0.append(arg1.deactivated(True)))
                    self.pluginDeactivated.emit(self.__instances[i][1])

                for i in reversed(reloadChain):
                    self.__instances[i][1].unloaded() # We do not deinstantiate the plugin to ensure we can fall back to the previous version.

                # Load and re-activate the dependency chain.
                reloadedInstances: list[PluginBase] = []
                reloadContextes.reverse()
                for a, b in zip(reloadChain, baseInfo):
                    instance = self.__loadPlugin(self.__instances[a][0].path, True)
                    if instance.pluginId() != b[0] or instance.__class__.__name__ != b[1] or instance.dependencies() != b[2]:
                        raise PluginContext.PluginDefinitionMutatedException()
                    reloadedInstances.append(instance)
                for i in reloadedInstances:
                    i.loaded()

                for a, b in zip(reloadedInstances, reloadContextes):
                    dependencyInstances: list[PluginBase] = []
                    for k in a.dependencies():
                        dependencyInstances.append(
                            next((w for w in reloadedInstances + [inst for _, (_, inst) in self.__instances.items()] if w.pluginId() == k), None)
                        )
                    result = context.invokeOnMainThread(lambda arg0 = a, arg1 = dependencyInstances, arg2 = b: arg0.activated({instance.pluginId(): instance for instance in arg1}, arg2))
                    if not isinstance(result, list) or len(result) == 0:
                        context.pluginActivated.emit(a)
                    else:
                        if "--silent-plugin-exc" in sys.argv:
                            print("Plugin contains errors. Falling back to previous state...")

                            reloadedInstances = [] # Do not replace loaded instances.
                            for a, b in zip(reloadChain, reloadContextes):
                                self.__instances[a][1].loaded()
                                dependencyInstances: list[PluginBase] = []
                                for k in self.__instances[a][1].dependencies():
                                    dependencyInstances.append(self.__instances[k][1])
                                context.invokeOnMainThread(lambda arg0 = self.__instances[a][1], arg1 = dependencyInstances, arg2 = b: arg0.activated({instance.pluginId(): instance for instance in arg1}, arg2))
                                self.pluginActivated.emit(self.__instances[a][1])
                        else:
                            for i in result:
                                raise i

                for i in reloadedInstances:
                    self.__instances[i.pluginId()][1] = i

        def __atexit(self) -> None:
            """
            Remove all sources.
            """
            
            for v in self.__instances.values():
                v[0].removable = True
            sourceStack = list(reversed(self.__sources))
            for k in sourceStack:
                self.removeSource(k)


        class __PluginMetadata(object):
            """
            Plugin metadata.
            """
            pluginId    : str       = None  # Unique identifier to name this plugin across the plugin ecosystem.
            removable   : bool      = False # Whether this plugin can be removed (=True) or not (=False).
            path        : str       = None  # Absolute path to the directory where this plugin is located.
            source      : str       = None  # Absolute path to the source directory where this plugin was found.
            dependents  : list[str] = None  # List of plugins that depend on this plugin (for hot-reloading purposes).
            def __init__(self) -> None: 
                super().__init__()
                self.dependents = []

class PluginBase(QObject):
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
    def loaded(self) -> None: 
        """
        Called when the plugin is loaded.
        It is guaranteed that this method will be called before activated().
        It is not guaranteed that dependencies will already be loaded by the time this method is called.
        It is not guaranteed that this method is called on the main thread. To ensure this, use PluginContext.invokeOnMainThread.
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
                pluginSources.append(PluginContext.normalizedPath(i[2:]).strip('"\''))

        if PluginContext.gfx() and os.name == 'nt':
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('trevorvanhoof.sqrmelonfx')

       # Execute the application.
        pluginContext = PluginContext(pluginSources)
        pluginContext.exec_()

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
        cb.clipboard_append(PluginContext.normalizedPath(profileReportFn))
        cb.update()
        print("Path to the profiling report file has been copied to the clipboard.")

    else:
        _runPluginHostApp()
