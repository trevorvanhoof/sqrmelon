from typing import Union

from OpenGL.GL import shaders
from qt import *

from flex_project.utils.paths import canonicalAbsolutepath


class ProgramPool(QObject):
    def __init__(self) -> None:
        super().__init__()
        self._shaders: dict[tuple[str, int], int] = {}
        self._programs: dict[tuple[int, ...], int] = {}
        self._watcher = QFileSystemWatcher()
        self._watcher.fileChanged.connect(self._invalidate)
        # For each watched file, contains the shaders and programs keys to invalidate.
        self._watchMap: dict[str, tuple[list[tuple[str, int]], list[tuple[int, ...]]]] = {}
        # For each shader, contains watch map keys
        self._shaderPaths: dict[int, list[str]] = {}

    programsInvalidated = Signal()

    def _invalidate(self, path: str):
        path = canonicalAbsolutepath(path)
        if path not in self._watchMap:
            return
        shaders, programs = self._watchMap[path]
        for key in shaders:
            del self._shaderPaths[self._shaders[key]]
            del self._shaders[key]
        for key in programs:
            del self._programs[key]
        del self._watchMap[path]
        self._watcher.removePath(path)

    def shader(self, paths: tuple[str, ...], shaderType: int) -> int:
        key = ''.join(paths), shaderType
        if key in self._shaders:
            return self._shaders[key]
        stitches = []
        for path in paths:
            path = canonicalAbsolutepath(path)
            with open(path) as fh:
                stitches.append(fh.read())
        inst = shaders.compileShader('\n'.join(stitches), shaderType)
        for path in paths:
            path = canonicalAbsolutepath(path)
            self._watcher.addPath(path)
            self._watchMap.setdefault(path, ([], []))[0].append(key)
            self._shaderPaths.setdefault(inst, []).append(path)
        self._shaders[key] = inst
        return inst

    def program(self, *shaderArgs: Union[int, tuple[tuple[str, ...], int]]) -> int:
        instances = []
        for element in shaderArgs:
            if isinstance(element, int):
                instances.append(element)
            else:
                paths, shaderType = element
                instances.append(self.shader(paths, shaderType))
        key = tuple(instances)
        if key in self._programs:
            return self._programs[key]
        inst = shaders.compileProgram(*instances)
        for shader in instances:
            for path in self._shaderPaths.get(shader, []):
                self._watchMap[path][1].append(key)
        self._programs[key] = inst
        return inst
