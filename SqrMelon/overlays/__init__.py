"""
Module to load and manage the textures on this folder.
Loads all PNG files into GL textures on initialization.
"""
import os
from typing import Optional

from OpenGL.GL import GL_TEXTURE_2D, GL_UNPACK_ALIGNMENT, glBindTexture, glGenTextures, glPixelStorei

from buffers import Texture
from fileutil import FilePath
from projutil import gSettings
from qt import *
from qtutil import ColorBox, EnumBox, hlayout


def loadImage(filePath: str, tile: bool = True) -> Texture:
    assert isinstance(filePath, FilePath)
    texId = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texId)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    img = QImage(filePath)
    img.convertTo(QImage.Format.Format_RGBA8888)
    img.mirror(False, True)
    return Texture(Texture.RGBA8, img.width(), img.height(), tile, img.bits())


class Overlays(QWidget):
    _overlayDir = FilePath(__file__).abs().parent()
    _overlayNames = ['None'] + list(sorted(os.path.splitext(x)[0] for x in _overlayDir.iter() if x.endswith('.png')))
    _overlayCache: dict[int, Optional[Texture]] = {}

    changed = Signal()

    def __init__(self) -> None:
        super(Overlays, self).__init__()
        layout = hlayout()
        self.setLayout(layout)

        enm = EnumBox(Overlays._overlayNames)
        enm.setValue(self.overlayIndex())
        layout.addWidget(enm)
        enm.valueChanged.connect(self.setOverlayIndex)
        layout.addWidget(enm)

        clr = ColorBox(self.overlayColor())
        layout.addWidget(clr)
        clr.valueChanged.connect(self.setOverlayColor)
        layout.addWidget(clr)

    def colorBuffer(self) -> Optional[Texture]:
        idx = self.overlayIndex()
        if idx <= 0:
            return None
        img = Overlays._overlayCache.get(idx, None)
        if img:
            return img
        fpath = Overlays._overlayDir.join(Overlays._overlayNames[idx] + '.png')
        if not fpath.exists():
            return None
        img = loadImage(fpath)
        Overlays._overlayCache[idx] = img
        return img

    @staticmethod
    def overlayIndex() -> int:
        return int(gSettings.value('overlayIndex', 0))  # type: ignore

    def setOverlayIndex(self, index: int) -> None:
        gSettings.setValue('overlayIndex', index)
        self.changed.emit()

    @staticmethod
    def overlayColor() -> QColor:
        return QColor(gSettings.value('overlayColor', qRgba(255, 255, 255, 255)))

    def setOverlayColor(self, color: QColor) -> None:
        gSettings.setValue('overlayColor', color.rgba())
        self.changed.emit()
