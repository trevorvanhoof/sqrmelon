"""Utility that wraps OpenGL textures, frame buffers and render buffers."""
import contextlib
import struct
from typing import Iterable, Optional

from OpenGL.GL import (GL_BYTE, GL_CLAMP_TO_EDGE, GL_COLOR_ATTACHMENT0, GL_DEPTH24_STENCIL8, GL_DEPTH32F_STENCIL8, GL_DEPTH_ATTACHMENT, GL_DEPTH_COMPONENT, GL_DEPTH_COMPONENT16, GL_DEPTH_COMPONENT24, GL_DEPTH_COMPONENT32F, GL_DEPTH_STENCIL, GL_DEPTH_STENCIL_ATTACHMENT, GL_FLOAT, GL_FLOAT_32_UNSIGNED_INT_24_8_REV, GL_FRAMEBUFFER, GL_HALF_FLOAT, GL_INT, GL_LINEAR, GL_R11F_G11F_B10F, GL_R16F, GL_R16I, GL_R16UI, GL_R32F, GL_R32I, GL_R32UI, GL_R8, GL_R8_SNORM, GL_R8I, GL_R8UI, GL_RED, GL_RED_INTEGER, GL_REPEAT, GL_RG, GL_RG16F, GL_RG16I, GL_RG16UI, GL_RG32F, GL_RG32I, GL_RG32UI, GL_RG8, GL_RG8_SNORM, GL_RG8I, GL_RG8UI, GL_RG_INTEGER, GL_RGB, GL_RGB10_A2, GL_RGB10_A2UI, GL_RGB16F, GL_RGB16I, GL_RGB16UI, GL_RGB32F, GL_RGB32I, GL_RGB32UI, GL_RGB565, GL_RGB5_A1, GL_RGB8, GL_RGB8_SNORM, GL_RGB8I, GL_RGB8UI, GL_RGB9_E5, GL_RGB_INTEGER, GL_RGBA, GL_RGBA16F, GL_RGBA16I, GL_RGBA16UI, GL_RGBA32F, GL_RGBA32I, GL_RGBA32UI, GL_RGBA4, GL_RGBA8, GL_RGBA8_SNORM, GL_RGBA8I, GL_RGBA8UI, GL_RGBA_INTEGER,
                       GL_SHORT, GL_SRGB8, GL_SRGB8_ALPHA8, GL_STENCIL_ATTACHMENT, GL_TEXTURE_2D, GL_TEXTURE_3D, GL_TEXTURE_MAG_FILTER, GL_TEXTURE_MIN_FILTER, GL_TEXTURE_WRAP_R, GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T, GL_UNSIGNED_BYTE, GL_UNSIGNED_INT, GL_UNSIGNED_INT_10F_11F_11F_REV, GL_UNSIGNED_INT_24_8, GL_UNSIGNED_INT_2_10_10_10_REV, GL_UNSIGNED_INT_5_9_9_9_REV, GL_UNSIGNED_SHORT, GL_UNSIGNED_SHORT_4_4_4_4, GL_UNSIGNED_SHORT_5_5_5_1, GL_UNSIGNED_SHORT_5_6_5, glBindFramebuffer, glBindTexture, glDrawBuffers, glFramebufferTexture2D, glGenFramebuffers, glGenTextures, glGetTexImage, glTexImage2D, glTexImage3D, glTexParameteri, glViewport)

from fileutil import FilePath
from qt import QImage


class Texture:
    """Creates a GL texture2D.

    The static members below are all color formats at this point in time &
    make it only 1 variable instead of 3. Call use() to bind the texture with Gl.
    """
    # TODO: Make this an enum of namedtuples?
    R8 = GL_R8, GL_RED, GL_UNSIGNED_BYTE
    R8_SNORM = GL_R8_SNORM, GL_RED, GL_BYTE
    R16F = GL_R16F, GL_RED, GL_HALF_FLOAT, GL_FLOAT
    R32F = GL_R32F, GL_RED, GL_FLOAT
    R8UI = GL_R8UI, GL_RED_INTEGER, GL_UNSIGNED_BYTE
    R8I = GL_R8I, GL_RED_INTEGER, GL_BYTE
    R16UI = GL_R16UI, GL_RED_INTEGER, GL_UNSIGNED_SHORT
    R16I = GL_R16I, GL_RED_INTEGER, GL_SHORT
    R32UI = GL_R32UI, GL_RED_INTEGER, GL_UNSIGNED_INT
    R32I = GL_R32I, GL_RED_INTEGER, GL_INT
    RG8 = GL_RG8, GL_RG, GL_UNSIGNED_BYTE
    RG8_SNORM = GL_RG8_SNORM, GL_RG, GL_BYTE
    RG16F = GL_RG16F, GL_RG, GL_HALF_FLOAT, GL_FLOAT
    RG32F = GL_RG32F, GL_RG, GL_FLOAT
    RG8UI = GL_RG8UI, GL_RG_INTEGER, GL_UNSIGNED_BYTE
    RG8I = GL_RG8I, GL_RG_INTEGER, GL_BYTE
    RG16UI = GL_RG16UI, GL_RG_INTEGER, GL_UNSIGNED_SHORT
    RG16I = GL_RG16I, GL_RG_INTEGER, GL_SHORT
    RG32UI = GL_RG32UI, GL_RG_INTEGER, GL_UNSIGNED_INT
    RG32I = GL_RG32I, GL_RG_INTEGER, GL_INT
    RGB8 = GL_RGB8, GL_RGB, GL_UNSIGNED_BYTE
    SRGB8 = GL_SRGB8, GL_RGB, GL_UNSIGNED_BYTE
    RGB565 = GL_RGB565, GL_RGB, GL_UNSIGNED_BYTE, GL_UNSIGNED_SHORT_5_6_5
    RGB8_SNORM = GL_RGB8_SNORM, GL_RGB, GL_BYTE
    R11F_G11F_B10F = GL_R11F_G11F_B10F, GL_RGB, GL_UNSIGNED_INT_10F_11F_11F_REV, GL_HALF_FLOAT, GL_FLOAT
    RGB9_E5 = GL_RGB9_E5, GL_RGB, GL_UNSIGNED_INT_5_9_9_9_REV, GL_HALF_FLOAT, GL_FLOAT
    RGB16F = GL_RGB16F, GL_RGB, GL_HALF_FLOAT, GL_FLOAT
    RGB32F = GL_RGB32F, GL_RGB, GL_FLOAT
    RGB8UI = GL_RGB8UI, GL_RGB_INTEGER, GL_UNSIGNED_BYTE
    RGB8I = GL_RGB8I, GL_RGB_INTEGER, GL_BYTE
    RGB16UI = GL_RGB16UI, GL_RGB_INTEGER, GL_UNSIGNED_SHORT
    RGB16I = GL_RGB16I, GL_RGB_INTEGER, GL_SHORT
    RGB32UI = GL_RGB32UI, GL_RGB_INTEGER, GL_UNSIGNED_INT
    RGB32I = GL_RGB32I, GL_RGB_INTEGER, GL_INT
    RGBA8 = GL_RGBA8, GL_RGBA, GL_UNSIGNED_BYTE
    SRGB8_ALPHA8 = GL_SRGB8_ALPHA8, GL_RGBA, GL_UNSIGNED_BYTE
    RGBA8_SNORM = GL_RGBA8_SNORM, GL_RGBA, GL_BYTE
    RGB5_A1 = GL_RGB5_A1, GL_RGBA, GL_UNSIGNED_BYTE, GL_UNSIGNED_SHORT_5_5_5_1, GL_UNSIGNED_INT_2_10_10_10_REV
    RGBA4 = GL_RGBA4, GL_RGBA, GL_UNSIGNED_BYTE, GL_UNSIGNED_SHORT_4_4_4_4
    RGB10_A2 = GL_RGB10_A2, GL_RGBA, GL_UNSIGNED_INT_2_10_10_10_REV
    RGBA16F = GL_RGBA16F, GL_RGBA, GL_HALF_FLOAT, GL_FLOAT
    RGBA32F = GL_RGBA32F, GL_RGBA, GL_FLOAT
    RGBA8UI = GL_RGBA8UI, GL_RGBA_INTEGER, GL_UNSIGNED_BYTE
    RGBA8I = GL_RGBA8I, GL_RGBA_INTEGER, GL_BYTE
    RGB10_A2UI = GL_RGB10_A2UI, GL_RGBA_INTEGER, GL_UNSIGNED_INT_2_10_10_10_REV
    RGBA16UI = GL_RGBA16UI, GL_RGBA_INTEGER, GL_UNSIGNED_SHORT
    RGBA16I = GL_RGBA16I, GL_RGBA_INTEGER, GL_SHORT
    RGBA32I = GL_RGBA32I, GL_RGBA_INTEGER, GL_INT
    RGBA32UI = GL_RGBA32UI, GL_RGBA_INTEGER, GL_UNSIGNED_INT
    DEPTH_COMPONENT16 = GL_DEPTH_COMPONENT16, GL_DEPTH_COMPONENT, GL_UNSIGNED_SHORT, GL_UNSIGNED_INT
    DEPTH_COMPONENT24 = GL_DEPTH_COMPONENT24, GL_DEPTH_COMPONENT, GL_UNSIGNED_INT
    DEPTH_COMPONENT32F = GL_DEPTH_COMPONENT32F, GL_DEPTH_COMPONENT, GL_FLOAT
    DEPTH24_STENCIL8 = GL_DEPTH24_STENCIL8, GL_DEPTH_STENCIL, GL_UNSIGNED_INT_24_8
    DEPTH32F_STENCIL8 = GL_DEPTH32F_STENCIL8, GL_DEPTH_STENCIL, GL_FLOAT_32_UNSIGNED_INT_24_8_REV
    # common aliases
    FLOAT_CHANNEL = GL_R32F, GL_RED, GL_FLOAT
    FLOAT_COLOR = GL_RGBA32F, GL_RGBA, GL_FLOAT
    FLOAT_DEPTH = GL_DEPTH_COMPONENT32F, GL_DEPTH_COMPONENT, GL_FLOAT
    FLOAT_DEPTH_STENCIL = GL_DEPTH32F_STENCIL8, GL_DEPTH_STENCIL, GL_FLOAT_32_UNSIGNED_INT_24_8_REV

    def __init__(self, channels: tuple[int, int, int], width: int, height: int, tile: bool = True, data: Optional[bytes] = None) -> None:
        self._width = width
        self._height = height

        self._id = glGenTextures(1)

        self.use()
        glTexImage2D(GL_TEXTURE_2D, 0, channels[0], width, height, 0, channels[1], channels[2], data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        if not tile:
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        else:
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)

    def id(self) -> int:
        """Returns the internal OpenGL handle."""
        return self._id

    def use(self) -> None:
        glBindTexture(GL_TEXTURE_2D, self._id)

    def width(self) -> int:
        return self._width

    def height(self) -> int:
        return self._height

    def save(self, filePath: FilePath) -> None:
        """Saves the image to disk using QImage.

        If the file extension is 'r32' we get the
        red channel as float32 instead and dump it raw.
        This was used to generate heightfields with the
        tool and then save them to load offline later.
        """
        self.use()
        pixels = self._width * self._height
        buffer = b'\0' * (pixels * 4)
        if filePath.hasExt('.r32'):
            # heightfield export
            glGetTexImage(GL_TEXTURE_2D, 0, GL_RED, GL_FLOAT, buffer)
            with filePath.editBinary() as fh:
                fh.write(struct.pack(f'{pixels}f', *buffer))
            return
        glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_UNSIGNED_BYTE, buffer)
        img = QImage(buffer, self._width, self._height, QImage.Format.Format_RGBA8888)
        img.mirror(False, True)
        img.save(filePath)


class Texture3D:
    def __init__(self, channels: tuple[int, int, int], resolution: int, tile: bool = True, data: Optional[bytes] = None) -> None:
        # for channels refer to the options in Texture
        self._width = resolution
        self._height = resolution
        self._depth = resolution

        self._id = glGenTextures(1)

        self.use()
        glTexImage3D(GL_TEXTURE_3D, 0, channels[0], resolution, resolution, resolution, 0, channels[1], channels[2], data)
        glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        if not tile:
            glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

        # To render into 3D textures we first render into a 2D texture
        # so we can just do 1 draw call for all texels, then read pixels,
        # and upload the same array to the 3D texture.
        self.original: Optional[Texture] = None

    def use(self) -> None:
        glBindTexture(GL_TEXTURE_3D, self._id)

    def width(self) -> int:
        return self._width

    def height(self) -> int:
        return self._height

    def depth(self) -> int:
        return self._depth

    def id(self) -> int:
        return self._id


class FrameBuffer:
    """
    Utility to set up a frame buffer and manage its color & render buffers.

    Call use() to render into the buffer and automatically bind all the color buffers as well as adjust glViewport.
    """

    def __init__(self, width: int, height: int) -> None:
        self.__id = glGenFramebuffers(1)
        self.__stats: list[Optional[Texture]] = [None]
        self.__buffers: list[int] = []
        assert isinstance(width, int)
        assert isinstance(height, int)
        self.__width = width
        self.__height = height

    def width(self) -> int:
        return self.__width

    def height(self) -> int:
        return self.__height

    def use(self, soft: bool = False) -> None:
        """
        Soft binding avoids setting the viewport and raw buffers.
        Used for setting up the color buffer bindings.
        """
        glBindFramebuffer(GL_FRAMEBUFFER, self.__id)
        if soft:
            return
        glDrawBuffers(len(self.__buffers), self.__buffers)
        glViewport(0, 0, self.__width, self.__height)

    @contextlib.contextmanager
    def useInContext(self, screenSize: tuple[int, int], soft: bool = False) -> None:
        self.use(soft)
        yield
        FrameBuffer.clear()
        glViewport(0, 0, *screenSize)

    @staticmethod
    def clear() -> None:
        from sceneview3d import SceneView
        glBindFramebuffer(GL_FRAMEBUFFER, SceneView.screenFBO)

    def id(self) -> int:
        return self.__id

    def addTexture(self, texture: Texture):
        # TODO: check if given texture has right channels (depth, rgba, depth-stencil), etc
        assert (texture.width() == self.__width)
        assert (texture.height() == self.__height)
        bid = GL_COLOR_ATTACHMENT0 + len(self.__stats)
        self.__stats.append(texture)
        self.__buffers.append(bid)
        self.use(True)
        glFramebufferTexture2D(GL_FRAMEBUFFER, bid, GL_TEXTURE_2D, texture.id(), 0)

    def initDepthStencil(self, depthStencil: Texture):
        # TODO: check if given texture has right channels DEPTH_STENCIL texture
        if self.__stats[0] is not None:
            raise RuntimeError('FrameBuffer already has a depth, stencil or depth_stencil attachment.')
        self.use(True)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_TEXTURE_2D, depthStencil.id(), 0)
        self.__stats[0] = depthStencil

    def initDepth(self, depth: Texture):
        # TODO: check if given texture has right channels, DEPTH texture
        if self.__stats[0] is not None:
            raise RuntimeError('FrameBuffer already has a depth, stencil or depth_stencil attachment.')
        self.use(True)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, depth.id(), 0)
        self.__stats[0] = depth

    def initStencil(self, stencil: Texture):
        # TODO: check if given texture has right channels, STENCIL texture
        if self.__stats[0] is not None:
            raise RuntimeError('FrameBuffer already has a depth, stencil or depth_stencil attachment.')
        self.use(True)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_STENCIL_ATTACHMENT, GL_TEXTURE_2D, stencil.id(), 0)
        self.__stats[0] = stencil

    def depth(self) -> Texture:
        return self.__stats[0]

    def textures(self) -> Iterable[Texture]:
        for i in range(1, len(self.__stats)):
            yield self.__stats[i]
