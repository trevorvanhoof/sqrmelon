"""
Module to load and manage the textures on this folder.
Loads all PNG files into GL textures on initialization.
"""
import fileutil
from util import gSettings
from qtutil import *
import os
from buffers import *


def loadImage(filePath, tile=True):
    texId = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texId)

    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

    tex = QGLWidget.convertToGLFormat(QImage(filePath.replace('\\', '/')))

    return Texture(Texture.RGBA8, tex.width(), tex.height(), tile, ctypes.c_void_p(int(tex.bits())))


class Overlays(QWidget):
    _overlayDir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    _overlayNames = ['None'] + list(sorted(os.path.splitext(x)[0] for x in os.listdir(_overlayDir) if x.endswith('.png')))
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
        fpath = os.path.join(Overlays._overlayDir, Overlays._overlayNames[idx] + '.png')
        if not fileutil.exists(fpath):
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
