from qtutil import *
from fileutil import FilePath
import os

__iconCache: dict[str, QIcon] = {}


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


def getImage(iconName: str) -> QIcon:
    if iconName not in __iconCache:
        iconPath = _getPath(iconName)
        if iconPath.hasExt('ico'):
            image = QIcon(iconPath)
        else:
            image = QIcon(QPixmap(iconPath))
        if image is None or image.isNull():
            raise Exception('Icon not loaded: %s' % iconPath)
        __iconCache[iconName] = image
    else:
        image = __iconCache[iconName]
    return image
