from abc import ABC
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

from OpenGL.GL import GL_BYTE, GL_FLOAT, GL_HALF_FLOAT, GL_INT, GL_LINE_LOOP, GL_LINE_STRIP, GL_LINES, GL_POINTS, GL_SHORT, GL_TRIANGLE_FAN, GL_TRIANGLE_STRIP, GL_TRIANGLES, GL_UNSIGNED_BYTE, GL_UNSIGNED_INT, GL_UNSIGNED_SHORT


class MeshAttributeDimensions(IntEnum):
    Vec1 = 1
    Vec2 = 2
    Vec3 = 3
    Vec4 = 4


class MeshAttributeType(IntEnum):
    F32 = GL_FLOAT
    F16 = GL_HALF_FLOAT
    U8 = GL_UNSIGNED_BYTE
    I8 = GL_BYTE
    U16 = GL_UNSIGNED_SHORT
    I16 = GL_SHORT
    U32 = GL_UNSIGNED_INT
    I32 = GL_INT


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


@dataclass
class Storagebuffer(_Named):
    sizeInBytes: int = 0


@dataclass
class MeshAttribute(_Named):
    location: int = 0
    dimensions: MeshAttributeDimensions = MeshAttributeDimensions.Vec3
    type: MeshAttributeType = MeshAttributeType.F32

    def __post_init__(self):
        self.dimensions = MeshAttributeDimensions(self.dimensions)
        self.type = getattr(MeshAttributeType, self.type)  # type: ignore


@dataclass
class MeshLayout(_Named):
    attributes: tuple[MeshAttribute, ...] = tuple()
    instanceAttributes: tuple[MeshAttribute, ...] = tuple()

    def __post_init__(self):
        self.attributes = [MeshAttribute(**kwargs) for kwargs in self.attributes]  # type: ignore
        self.instanceAttributes = [MeshAttribute(**kwargs) for kwargs in self.instanceAttributes]  # type: ignore


@dataclass
class Command(_Named, ABC):
    ...


@dataclass
class BindFramebuffer(Command):
    # Framebuffer to bind, None targets the backbuffer instead.
    framebuffer: Optional[str] = None


@dataclass
class Clear(Command):
    # Which clear flags to use on the current framebuffer.
    color: bool = False
    depth: bool = True


@dataclass
class DrawRect(Command):
    # File paths to concatenate and use as shaders.
    fragment: Optional[tuple[str, ...]] = tuple()
    # Frame buffer name and color buffer index pairs to bind to uImages.
    textures: tuple[tuple[str, int], ...] = tuple()


@dataclass
class DrawMesh(DrawRect):
    # File paths to concatenate and use as shaders.
    vertex: Optional[tuple[str, ...]] = tuple()
    geometry: Optional[tuple[str, ...]] = tuple()
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

    def __post_init__(self):
        self.primitive = getattr(DrawPrimitive, self.primitive)  # type: ignore


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


def _unpack_commands(commands: list) -> tuple[Command, ...]:
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
    framebuffers: tuple[Framebuffer, ...] = tuple()
    storagebuffers: tuple[Storagebuffer, ...] = tuple()
    meshLayouts: tuple[MeshLayout, ...] = tuple()
    staticDraw: tuple[Command, ...] = tuple()

    def __post_init__(self) -> None:
        self.framebuffers = [Framebuffer(**kwargs) for kwargs in self.framebuffers]  # type: ignore
        self.storagebuffers = [Storagebuffer(**kwargs) for kwargs in self.storagebuffers]  # type: ignore
        self.meshLayouts = [MeshLayout(**kwargs) for kwargs in self.meshLayouts]  # type: ignore
        self.staticDraw = _unpack_commands(self.staticDraw)  # type: ignore


@dataclass
class Template:
    # Templates only have to run a list of commands for now.
    draw: tuple[Command, ...] = tuple()

    def __post_init__(self) -> None:
        self.draw = _unpack_commands(self.draw)  # type: ignore
