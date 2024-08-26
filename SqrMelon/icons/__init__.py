import os
from typing import Union

from fileutil import FilePath
from qt import QIcon, QPixmap

__iconCache: dict[str, Union[QPixmap, QIcon]] = {}


def get(iconName: str) -> QIcon:
    """
    Retrieves a bitmap from the icon cache and
    returns a new QIcon using a cached version of the bitmap.
    The icon name will be used as a key in the cache
    @param iconName: filename without .png extension
    @return: QtGui.QIcon
    """
    return QIcon(getImage(iconName))


_FORMATS = 'svg', 'png', 'ico'


def _getPath(iconName: str) -> FilePath:
    folder = FilePath(os.path.dirname(__file__))
    for fmt in _FORMATS:
        path = folder.join(iconName + '.' + fmt)
        if path.exists():
            return path
    raise Exception('Icon not found: %s' % iconName)


def getImage(iconName: str) -> Union[QPixmap, QIcon]:
    if iconName not in __iconCache:
        iconPath = _getPath(iconName)
        if iconPath.hasExt('ico'):
            image: Union[QIcon, QPixmap] = QIcon(iconPath)
        else:
            image = QPixmap(iconPath)
        if image is None or image.isNull():
            raise Exception('Icon not loaded: %s' % iconPath)
        __iconCache[iconName] = image
    else:
        image = __iconCache[iconName]
    return image
