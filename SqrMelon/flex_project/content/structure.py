import struct
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional

from OpenGL.GL import GL_BYTE, GL_COMPUTE_SHADER, GL_FLOAT, GL_FRAGMENT_SHADER, GL_INT, GL_LINE_LOOP, GL_LINE_STRIP, GL_LINES, GL_POINTS, GL_SHORT, GL_TRIANGLE_FAN, GL_TRIANGLE_STRIP, GL_TRIANGLES, GL_UNSIGNED_BYTE, GL_UNSIGNED_INT, GL_UNSIGNED_SHORT, GL_VERTEX_SHADER, GL_GEOMETRY_SHADER

from flex_project.export.binary_pool import BinaryPool, multiPack, serializeArray, serializePolhymorphicArray


class MeshAttributeDimensions(IntEnum):
    Vec1 = 1
    Vec2 = 2
    Vec3 = 3
    Vec4 = 4


class MeshAttributeType(IntEnum):
    I8 = GL_BYTE
    U8 = GL_UNSIGNED_BYTE
    I16 = GL_SHORT
    U16 = GL_UNSIGNED_SHORT
    I32 = GL_INT
    U32 = GL_UNSIGNED_INT
    F32 = GL_FLOAT


class DrawPrimitive(IntEnum):
    Points = GL_POINTS
    Lines = GL_LINES
    LineLoop = GL_LINE_LOOP
    LineStrip = GL_LINE_STRIP
    Triangles = GL_TRIANGLES
    TriangleStrip = GL_TRIANGLE_STRIP
    TriangleFan = GL_TRIANGLE_FAN


@dataclass
class _Named(ABC):
    # Names are sometimes used to reference assets,
    # and are otherwise useful for debugging.
    name: str = ''


@dataclass
class Framebuffer(_Named):
    # Number of color buffers attached to this framebuffer.
    outputs: int = 1
    # Optional depth buffer for depth testing to work.
    depth: bool = False
    # Use screen resolution / factorm width and height must be 0 if this is not 0.
    factor: int = 1
    # Use given resolution, factor must be 0 if this is not 0, and then both of them must be non-0.
    width: int = 0
    height: int = 0

    def serialize(self, target: BinaryPool) -> bytes:
        return multiPack('BBHH', (self.outputs | (int(self.depth) << 7), self.factor, self.width, self.height))


@dataclass
class Storagebuffer(_Named):
    sizeInBytes: int = 0

    def serialize(self, target: BinaryPool) -> bytes:
        return multiPack('I', self.sizeInBytes)


@dataclass
class MeshAttribute(_Named):
    location: int = 0
    dimensions: MeshAttributeDimensions = MeshAttributeDimensions.Vec3
    type: MeshAttributeType = MeshAttributeType.F32

    def __post_init__(self) -> None:
        self.dimensions = MeshAttributeDimensions(self.dimensions)
        self.type = getattr(MeshAttributeType, self.type)  # type: ignore

    def serialize(self, target: BinaryPool) -> bytes:
        offset = int(self.type.value) - int(GL_BYTE)
        assert 0 <= offset <= 6
        size = int(self.dimensions.value) - 1
        assert 0 <= size <= 3
        # Note: if this assert goes off we can increase MeshAttribute to be 16 instead of 8 bits.
        assert 0 <= self.location <= 7
        packed = (self.location << 5) | (size << 3) | offset
        return multiPack('B', packed)


@dataclass
class MeshLayout(_Named):
    attributes: tuple[MeshAttribute, ...] = tuple()
    instanceAttributes: tuple[MeshAttribute, ...] = tuple()

    def __post_init__(self) -> None:
        self.attributes = tuple(MeshAttribute(**kwargs) for kwargs in self.attributes)  # type: ignore
        self.instanceAttributes = tuple(MeshAttribute(**kwargs) for kwargs in self.instanceAttributes)  # type: ignore

    def serialize(self, target: BinaryPool) -> bytes:
        return serializeArray(self.attributes, target) + serializeArray(self.instanceAttributes, target)


def _allSubclasses(cls):
    result = []
    for subclass in cls.__subclasses__():
        result.append(subclass)
        result.extend(_allSubclasses(subclass))
    return result


@dataclass
class Command(_Named, ABC):
    @abstractmethod
    def serialize(self, target: BinaryPool, *args) -> bytes:
        subs = _allSubclasses(Command)
        return multiPack('B', subs.index(self.__class__))


@dataclass
class BindFramebuffer(Command):
    # Framebuffer to bind, None targets the backbuffer instead.
    framebuffer: Optional[str] = None

    def serialize(self, target: BinaryPool, *args) -> bytes:
        data = super().serialize(target, *args)
        if not self.framebuffer:
            return data + multiPack('B', 255)
        return data + multiPack('B', args[0][self.framebuffer])


@dataclass
class Clear(Command):
    # Which clear flags to use on the current framebuffer.
    color: bool = False
    depth: bool = True

    def serialize(self, target: BinaryPool, *args) -> bytes:
        data = super().serialize(target, *args)
        return data + multiPack('B', (int(self.color) << 1) | int(self.depth))


def _resolveShaderPaths(filePaths: tuple[str, ...], *shaderFolders: str) -> tuple[str, ...]:
    result = []
    for filePath in filePaths:
        for shaderFolder in shaderFolders:
            option = os.path.join(shaderFolder, filePath)
            if os.path.exists(option):
                result.append(option)
                break
        else:
            raise FileNotFoundError
    return tuple(result)


@dataclass
class DrawRect(Command):
    # Frame buffer name and color buffer index pairs to bind to uImages.
    textures: tuple[tuple[str, int], ...] = tuple()
    # File paths to concatenate and use as shaders.
    fragment: tuple[str, ...] = tuple()

    def resolvedFragment(self, *shaderFolders: str) -> tuple[str, ...]:
        return _resolveShaderPaths(self.fragment, *shaderFolders)

    def __post_init__(self) -> None:
        self.fragment = tuple(self.fragment)
        self.textures = tuple(tuple(texture) for texture in self.textures)

    @staticmethod
    def serializeIntList(source: list[int], target: BinaryPool) -> bytes:
        return multiPack('II', (len(source), target.ensureExists(multiPack(f'{len(source)}I', source))))

    def serialize(self, target: BinaryPool, *args) -> bytes:
        data = Command.serialize(self, target, *args)
        data += self.serializeIntList([args[3][texture] for texture in self.textures], target)
        shader = target.ensureShaderExists(self.fragment, GL_FRAGMENT_SHADER)
        data += multiPack('B', target.ensureProgramExists(shader))
        return data


@dataclass
class DrawMesh(DrawRect):
    # File paths to concatenate and use as shaders.
    vertex: tuple[str, ...] = tuple()
    geometry: tuple[str, ...] = tuple()
    # Storage buffer to bind as array.
    vbo: Optional[str] = None
    # Storage buffer to bind as elements.
    ibo: Optional[str] = None
    # Storage buffer to bind as second array.
    ivbo: Optional[str] = None
    # Mesh attribute layout to use.
    layout: str = ''
    # Number of vertices to draw.
    count: int = 0
    # Number of instances to draw.
    instanceCount: int = 1
    # Primitive type to use.
    primitive: DrawPrimitive = DrawPrimitive.Triangles

    def resolvedVertex(self, *shaderFolders: str) -> tuple[str, ...]:
        return _resolveShaderPaths(self.vertex, *shaderFolders)

    def resolvedGeometry(self, *shaderFolders: str) -> tuple[str, ...]:
        return _resolveShaderPaths(self.geometry, *shaderFolders)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.vertex = tuple(self.vertex)
        self.geometry = tuple(self.geometry)
        self.primitive = getattr(DrawPrimitive, self.primitive)  # type: ignore

    def serialize(self, target: BinaryPool, *args) -> bytes:
        data = Command.serialize(self, target, *args)
        data += self.serializeIntList([args[3][texture] for texture in self.textures], target)
        fragment = target.ensureShaderExists(self.fragment, GL_FRAGMENT_SHADER)
        vertex = target.ensureShaderExists(self.vertex, GL_VERTEX_SHADER)
        geometry = target.ensureShaderExists(self.geometry, GL_GEOMETRY_SHADER)
        data += struct.pack('B', target.ensureProgramExists(fragment, vertex, geometry))
        primitive = int(self.primitive.value) - int(GL_POINTS)
        assert 0 <= primitive <= 6
        data += multiPack('BBBBIIB',
                          (args[1][self.vbo] if self.vbo else 255,
                           args[1][self.ibo] if self.ibo else 255,
                           args[1][self.ivbo] if self.ivbo else 255,
                           args[2][self.layout],
                           self.count,
                           self.instanceCount,
                           primitive))
        return data


@dataclass
class DispatchCompute(Command):
    # Dispatch work group counts.
    groups: tuple[int, int, int] = 1, 1, 1
    # Which storage buffers to bind.
    # They get bound in the listed order, the location
    # starts at 0 and simply increments after each bind.
    storagebuffers: tuple[str, ...] = tuple()
    # File paths to concatenate and use as compute shader.
    compute: tuple[str, ...] = tuple()

    # TODO: Should this have a "textures" just like Draw? And should Draw have "storagebuffers"?

    def resolvedCompute(self, *shaderFolders: str) -> tuple[str, ...]:
        return _resolveShaderPaths(self.compute, *shaderFolders)

    def __post_init__(self) -> None:
        self.groups = tuple(self.groups)
        self.storagebuffers = tuple(self.storagebuffers)
        self.compute = tuple(self.compute)

    def serialize(self, target: BinaryPool, *args) -> bytes:
        data = super().serialize(target, *args)
        data += multiPack('III', self.groups)
        data += DrawRect.serializeIntList([args[1][name] for name in self.storagebuffers], target)
        shader = target.ensureShaderExists(self.compute, GL_COMPUTE_SHADER)
        data += multiPack('B', target.ensureProgramExists(shader))
        return data


def _unpackCommands(commands: list) -> tuple[Command, ...]:
    result = []
    for command in commands:
        clsName = command['command']
        del command['command']
        cls = globals()[clsName]
        inst = cls(**command)
        result.append(inst)
    return tuple(result)


@dataclass
class Project:
    # Project resource and static initialization definitions
    framebuffers: dict[str, Framebuffer] = field(default_factory=dict)
    storagebuffers: dict[str, Storagebuffer] = field(default_factory=dict)
    meshLayouts: dict[str, MeshLayout] = field(default_factory=dict)
    staticDraw: tuple[Command, ...] = tuple()

    def __post_init__(self) -> None:
        self.framebuffers = {name: Framebuffer(**kwargs) for name, kwargs in self.framebuffers.items()}  # type: ignore
        self.storagebuffers = {name: Storagebuffer(**kwargs) for name, kwargs in self.storagebuffers.items()}  # type: ignore
        self.meshLayouts = {name: MeshLayout(**kwargs) for name, kwargs in self.meshLayouts.items()}  # type: ignore
        self.staticDraw = _unpackCommands(self.staticDraw)  # type: ignore

    def commandSerializationArgs(self):
        framebufferNameToIndex = {name: index for (index, name) in enumerate(self.framebuffers)}
        storagebufferNameToIndex = {name: index for (index, name) in enumerate(self.storagebuffers)}
        meshLayoutNameToIndex = {name: index for (index, name) in enumerate(self.meshLayouts)}
        keyToCboIndex = {}
        cursor = 0
        for name, framebuffer in self.framebuffers.items():
            for cboIndex in range(framebuffer.outputs):
                keyToCboIndex[(name, cboIndex)] = cursor
                cursor += 1
        return framebufferNameToIndex, storagebufferNameToIndex, meshLayoutNameToIndex, keyToCboIndex

    def serialize(self, target: BinaryPool, *args) -> bytes:
        data = b''
        data += serializeArray(self.framebuffers.values(), target)
        data += serializeArray(self.storagebuffers.values(), target)
        data += serializeArray(self.meshLayouts.values(), target)
        # TODO: We could serialize all these commands as 1 blob and just store the number of commands
        #  to consume, and the offset; which still makes it an Array but without indexing support.
        #  Currently each command has its own place in memory allowing reuse but I don't see that happen very much.
        data += serializePolhymorphicArray(self.staticDraw, target, *args)
        return data


@dataclass
class Template:
    # Templates only have to run a list of commands for now.
    draw: tuple[Command, ...] = tuple()

    def __post_init__(self) -> None:
        self.draw = _unpackCommands(self.draw)  # type: ignore

    def serialize(self, target: BinaryPool, *args) -> bytes:
        # TODO: We could serialize all these commands as 1 blob and just store the number of commands
        #  to consume, and the offset; which still makes it an Array but without indexing support.
        #  Currently each command has its own place in memory allowing reuse but I don't see that happen very much.
        return serializePolhymorphicArray(self.draw, target, *args)
