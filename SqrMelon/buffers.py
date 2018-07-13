"""
Utility that wraps OpenGL textures, frame buffers and render buffers.
"""


import contextlib

from OpenGL.GL import *

import fileutil

class Texture(object):
    """
    Creates a GL texture2D.
    The static members below are all color formats at this point in time &
    make it only 1 variable instead of 3.

    Call use() to bind the texture with Gl.
    """
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

    def __init__(self, channels, width, height, tile=True, data=None):
        """
        :param channels: One of the above static members describing the pixel format.
        :param int width: Width in pixels
        :param int height: Height in pixels
        :param bool tile: Sets GL_CLAMP or GL_REPEAT accordingly.
        :param void* data: Can pass any ctypes pointer to fill the buffer on the GPU. Used for direct data upload from e.g. QImage or heightfields.
        """
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

    def id(self):
        return self._id

    def use(self):
        glBindTexture(GL_TEXTURE_2D, self._id)

    def width(self):
        return self._width

    def height(self):
        return self._height

    def save(self, filePath, ch=None):
        if filePath.endswith('.r32'):
            import struct
            # heightfield export
            pixels = self._width * self._height
            buffer = (ctypes.c_float * pixels)()
            glGetTexImage(GL_TEXTURE_2D, 0, GL_RED, GL_FLOAT, buffer)
            with fileutil.edit(filePath, 'wb') as fh:
                fh.write(struct.pack('%sf' % pixels, *buffer))
            return
        from PyQt4.QtGui import QImage
        pixels = self._width * self._height
        buffer = (ctypes.c_ubyte * (pixels * 4))()
        mirror = (ctypes.c_ubyte * (pixels * 4))()
        glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_UNSIGNED_BYTE, buffer)
        for i in xrange(0, pixels * 4, 4):
            if ch is None:
                mirror[i:i + 4] = (buffer[i + 2], buffer[i + 1], buffer[i], buffer[i + 3])
            else:
                mirror[i:i + 4] = (buffer[i + ch], buffer[i + ch], buffer[i + ch], 255)
        QImage(mirror, self._width, self._height, QImage.Format_ARGB32).save(filePath)


class Texture3D(Texture):
    def __init__(self, channels, resolution, tile=True, data=None):
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

    def use(self):
        glBindTexture(GL_TEXTURE_3D, self._id)

    def depth(self):
        return self._depth


class Cubemap(object):
    def __init__(self, channels, size, contents=None):
        self.__size = size
        self.__id = glGenTextures(1)

        self.use()
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        data = None
        for i in range(6):
            if contents is not None:
                data = contents[i]
            glTexImage2D(GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, 0, channels[0], size, size, 0, channels[1], channels[2], data)

    def id(self):
        return self.__id

    def use(self):
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.__id)

    def size(self):
        return self.__size


class RenderBuffer(object):
    R8 = GL_R8
    R8UI = GL_R8UI
    R8I = GL_R8I
    R16UI = GL_R16UI
    R16I = GL_R16I
    R32UI = GL_R32UI
    R32I = GL_R32I
    RG8 = GL_RG8
    RG8UI = GL_RG8UI
    RG8I = GL_RG8I
    RG16UI = GL_RG16UI
    RG16I = GL_RG16I
    RG32UI = GL_RG32UI
    RG32I = GL_RG32I
    RGB8 = GL_RGB8
    RGB565 = GL_RGB565
    RGBA8 = GL_RGBA8
    SRGB8_ALPHA8 = GL_SRGB8_ALPHA8
    RGB5_A1 = GL_RGB5_A1
    RGBA4 = GL_RGBA4
    RGB10_A2 = GL_RGB10_A2
    RGBA8UI = GL_RGBA8UI
    RGBA8I = GL_RGBA8I
    RGB10_A2UI = GL_RGB10_A2UI
    RGBA16UI = GL_RGBA16UI
    RGBA16I = GL_RGBA16I
    RGBA32I = GL_RGBA32I
    RGBA32UI = GL_RGBA32UI
    DEPTH_COMPONENT16 = GL_DEPTH_COMPONENT16
    DEPTH_COMPONENT24 = GL_DEPTH_COMPONENT24
    DEPTH_COMPONENT32F = GL_DEPTH_COMPONENT32F
    DEPTH24_STENCIL8 = GL_DEPTH24_STENCIL8
    DEPTH32F_STENCIL8 = GL_DEPTH32F_STENCIL8
    STENCIL_INDEX8 = GL_STENCIL_INDEX8
    # common aliases
    FLOAT_DEPTH = GL_DEPTH_COMPONENT32F
    FLOAT_DEPTH_STENCIL = GL_DEPTH32F_STENCIL8

    def __init__(self, channels, width, height):
        self.__id = glGenRenderbuffers(1)
        self.use()
        glRenderbufferStorage(GL_RENDERBUFFER, channels, width, height)

    def id(self):
        return self.__id

    def use(self):
        glBindRenderbuffer(GL_RENDERBUFFER, self.__id)


class FrameBuffer(object):
    """
    Utility to set up a frame buffer and manage its color & render buffers.

    Call use() to render into the buffer and automatically bind all the color buffers as well as adjust glViewport.
    """
    def __init__(self, width, height):
        self.__id = glGenFramebuffers(1)
        self.__stats = [None]
        self.__buffers = []
        self.__width = width
        self.__height = height

    def width(self):
        return self.__width

    def height(self):
        return self.__height

    def use(self, soft=False):
        glBindFramebuffer(GL_FRAMEBUFFER, self.__id)
        if soft:
            return
        glDrawBuffers(len(self.__buffers), self.__buffers)
        glViewport(0, 0, self.__width, self.__height)

    @contextlib.contextmanager
    def useInContext(self, screenSize, soft=False):
        self.use(soft)
        yield
        FrameBuffer.clear()
        glViewport(0, 0, *screenSize)

    @staticmethod
    def clear():
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

    def id(self):
        return self.__id

    def addTexture(self, texture):
        # TODO: check if given texture has right channels (depth, rgba, depth-stencil), etc
        assert (texture.width() == self.__width)
        assert (texture.height() == self.__height)
        bid = GL_COLOR_ATTACHMENT0 + len(self.__stats)
        self.__stats.append(texture)
        self.__buffers.append(bid)
        self.use(True)
        if isinstance(texture, RenderBuffer):
            glFramebufferRenderbuffer(GL_FRAMEBUFFER, bid, GL_RENDERBUFFER, texture.id())
        else:  # buffer is a texture
            glFramebufferTexture2D(GL_FRAMEBUFFER, bid, GL_TEXTURE_2D, texture.id(), 0)

    def initDepthStencil(self, depthStencil):
        # TODO: check if given texture has right channels DEPTH_STENCIL texture
        if self.__stats[0] is not None:
            raise RuntimeError('FrameBuffer already has a depth, stencil or depth_stencil attachment.')
        self.use(True)
        if isinstance(depthStencil, RenderBuffer):
            glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, depthStencil.id())
        else:  # buffer is a texture
            glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, depthStencil.id(), 0)
        self.__stats[0] = depthStencil

    def initDepth(self, depth):
        # TODO: check if given texture has right channels, DEPTH texture
        if self.__stats[0] is not None:
            raise RuntimeError('FrameBuffer already has a depth, stencil or depth_stencil attachment.')
        self.use(True)
        if isinstance(depth, RenderBuffer):
            glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, depth.id())
        else:  # buffer is a texture
            glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, depth.id(), 0)
        self.__stats[0] = depth

    def initStencil(self, stencil):
        # TODO: check if given texture has right channels, STENCIL texture
        if self.__stats[0] is not None:
            raise RuntimeError('FrameBuffer already has a depth, stencil or depth_stencil attachment.')
        self.use(True)
        if isinstance(stencil, RenderBuffer):
            glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_STENCIL_ATTACHMENT, GL_RENDERBUFFER, stencil.id())
        else:  # buffer is a texture
            glFramebufferTexture2D(GL_FRAMEBUFFER, GL_STENCIL_ATTACHMENT, GL_TEXTURE_2D, stencil.id(), 0)
        self.__stats[0] = stencil

    def depth(self):
        return self.__stats[0]

    def textures(self):
        for i in range(1, len(self.__stats)):
            yield self.__stats[i]
