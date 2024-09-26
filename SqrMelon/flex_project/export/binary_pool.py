import struct
from typing import Iterable, Protocol

from OpenGL.GL import GL_FRAGMENT_SHADER, GL_COMPUTE_SHADER, GL_VERTEX_SHADER, GL_GEOMETRY_SHADER


def multiPack(*args):
    assert len(args) % 2 == 0
    blobs = []
    for key, value in zip(args[::2], args[1::2]):
        if hasattr(value, '__iter__'):
            if not value:
                assert key[0] == '0'
                continue
            blob = struct.pack(key, *value)
            cmp = struct.unpack(key, blob)
            if isinstance(value[0], float):
                # TODO: compare almost equal
                ...
            else:
                assert tuple(value) == cmp
        else:
            blob = struct.pack(key, value)
            cmp = struct.unpack(key, blob)[0]
            if isinstance(value, float):
                assert abs(cmp - value) < 1e-5
            else:
                assert value == cmp
        blobs.append(blob)
    return b''.join(blobs)


class BinaryPool:
    def __init__(self) -> None:
        self._sequence: bytes = b''
        # ensureShaderExists() will return the existing index if the args are the same
        self._knownShaderIndices: dict[tuple[tuple[str, ...], int], int] = {}
        # ensureProgramExists() will return the existing index if the args are the same
        self._knownProgramIndices: dict[tuple[int, ...], int] = {}
        # Per mode: num shaders, per shader: num stitches, stitch offsets, tightly packed
        self._shaders: dict[int, list[int]] = {}
        self._addedShaders: dict[int, list[tuple[str, ...]]] = {}
        # Per program: num shaders, shader indices
        self._programs: list[int] = []
        self.maxStitches: int = 0

    def addShader(self, paths: tuple[str, ...], mode: int):
        # Avoid duplicate shaders
        keys = self._addedShaders.setdefault(mode, [])
        if paths in keys:
            return
        keys.append(paths)
        self.maxStitches = max(self.maxStitches, len(paths))
        # We group shaders by mode
        modeShaders = self._shaders.setdefault(mode, [])
        # We define each shader as a number of stitches and their offsets
        modeShaders.append(len(paths))
        for path in paths:
            with open(path, 'rb') as fh:
                modeShaders.append(self.ensureExists(fh.read() + b'\n\0'))

    def buildShaderIndices(self):
        for mode in (GL_FRAGMENT_SHADER, GL_COMPUTE_SHADER, GL_VERTEX_SHADER, GL_GEOMETRY_SHADER):
            for paths in self._addedShaders[mode]:
                self._knownShaderIndices[(paths, mode)] = len(self._knownShaderIndices)

    def ensureShaderExists(self, paths: tuple[str, ...], mode: int) -> int:
        key = paths, mode
        if key in self._knownShaderIndices:
            return self._knownShaderIndices[key]
        raise RuntimeError

    def numPrograms(self) -> int:
        return len(self._knownProgramIndices)

    def ensureProgramExists(self, *shaders: int) -> int:
        if shaders in self._knownProgramIndices:
            return self._knownProgramIndices[shaders]

        self._programs.append(len(shaders))
        self._programs.extend(shaders)

        nextIndex = len(self._knownProgramIndices)
        self._knownProgramIndices[shaders] = nextIndex
        return nextIndex

    def data(self) -> bytes:
        return self._sequence

    def shaderData(self) -> list[int]:
        output = []
        for mode in (GL_FRAGMENT_SHADER, GL_COMPUTE_SHADER, GL_VERTEX_SHADER, GL_GEOMETRY_SHADER):
            entries = self._shaders.get(mode, [])
            output.append(len(entries) // 2)
        for mode in (GL_FRAGMENT_SHADER, GL_COMPUTE_SHADER, GL_VERTEX_SHADER, GL_GEOMETRY_SHADER):
            entries = self._shaders.get(mode, [])
            output += entries
        return output

    def programData(self) -> list[int]:
        return self._programs

    def ensureExists(self, value: bytes) -> int:
        if not value:
            return 0
        try:
            index = self._sequence.index(value)
            assert self._sequence[index:index + len(value)] == value
            return index
        except ValueError:
            n = 1
            while n < len(value):
                if self._sequence.endswith(value[:-n]):
                    self._sequence += value[-n:]
                    index = len(self._sequence) - len(value)
                    assert self._sequence[index:index + len(value)] == value
                    return index
                n += 1
        self._sequence += value
        index = len(self._sequence) - len(value)
        assert self._sequence[index:index + len(value)] == value
        return index


class ISerializable(Protocol):
    def serialize(self, target: BinaryPool) -> bytes: ...


def serializeArray(iterable: Iterable[ISerializable], target: BinaryPool, *args) -> bytes:
    data = b''
    for serializable in iterable:
        data += serializable.serialize(target, *args)
    return multiPack('II', (len(iterable), target.ensureExists(data)))


def serializePolhymorphicArray(iterable: Iterable[ISerializable], target: BinaryPool, *args) -> bytes:
    data = b''
    for serializable in iterable:
        data += struct.pack('I', target.ensureExists(serializable.serialize(target, *args)))
    return multiPack('II', (len(iterable), target.ensureExists(data)))
