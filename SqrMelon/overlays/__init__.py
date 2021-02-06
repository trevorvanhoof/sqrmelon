"""
Module to load and manage the textures on this folder.
Loads all PNG files into GL textures on initialization.
"""
from fileutil import FilePath
from util import gSettings
from qtutil import *
import os
from buffers import *
import sys


def loadImage(filePath, tile=True):
    assert isinstance(filePath, FilePath)
    texId = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texId)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    tex = QGLWidget.convertToGLFormat(QImage(filePath))
    if sys.version_info.major == 3:
        return Texture(Texture.RGBA8, tex.width(), tex.height(), tile, tex.bits())
    else:
        return Texture(Texture.RGBA8, tex.width(), tex.height(), tile, ctypes.c_void_p(int(tex.bits())))


class Overlays(QWidget):
    _overlayDir = FilePath(__file__).abs().parent()
    _overlayNames = ['None'] + list(sorted(os.path.splitext(x)[0] for x in _overlayDir.iter() if x.endswith('.png')))
    _overlayCache = {}

    changed = pyqtSignal()

    def __init__(self):
        super(Overlays, self).__init__()
        l = hlayout()
        self.setLayout(l)

        enm = EnumBox(Overlays._overlayNames)
        enm.setValue(self.overlayIndex())
        l.addWidget(enm)
        enm.valueChanged.connect(self.setOverlayIndex)
        l.addWidget(enm)

        clr = ColorBox(self.overlayColor())
        l.addWidget(clr)
        clr.valueChanged.connect(self.setOverlayColor)
        l.addWidget(clr)

    def colorBuffer(self):
        idx = self.overlayIndex()
        if idx <= 0:
            return
        img = Overlays._overlayCache.get(idx, None)
        if img:
            return img
        fpath = Overlays._overlayDir.join(Overlays._overlayNames[idx] + '.png')
        if not fpath.exists():
            return
        img = loadImage(fpath)
        Overlays._overlayCache[idx] = img
        return img

    def overlayIndex(self):
        """
        :rtype: int
        """
        return gSettings.value('overlayIndex', 0)

    def setOverlayIndex(self, index):
        """
        :type index: int
        """
        gSettings.setValue('overlayIndex', index)
        self.changed.emit()

    def overlayColor(self):
        """
        :rtype: QColor
        """
        return QColor(gSettings.value('overlayColor', qRgba(255, 255, 255, 255)))

    def setOverlayColor(self, color):
        """
        :type color: QColor
        """
        gSettings.setValue('overlayColor', color.rgba())
        self.changed.emit()
