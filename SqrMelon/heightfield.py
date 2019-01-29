"""
Utility to load ".r32" files which are just raw binary float32 dumps of a single channel square texture with no extra data in the file.
"""

import stat
import mmap
import os
from math import sqrt
import ctypes
from buffers import Texture
from fileutil import FilePath


def loadHeightfield(filePath):
    assert isinstance(filePath, FilePath)
    # data is a single float32 color channel
    # so resolution is sqrt(number of floats)
    resolution = int(sqrt(os.path.getsize(filePath) / 4))
    # mmap can't return a pointer, so we have to use from_buffer, which in turn requires file to be writable
    os.chmod(filePath, stat.S_IREAD | stat.S_IWRITE | stat.S_IRGRP | stat.S_IROTH)
    fd = os.open(filePath, os.O_RDWR | os.O_BINARY)
    try:
        ptr = (ctypes.c_float * (resolution * resolution)).from_buffer(mmap.mmap(fd, 0))
        tex = Texture(Texture.R32F, resolution, resolution, tile=True, data=ptr)
    finally:
        os.close(fd)
    return tex
