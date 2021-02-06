from qtutil import *
from fileutil import FilePath
import os

__iconCache = {}


def get(iconName):
    """
    Retrieves an bitmap from the icon stash and
    returns a new QIcon using a cached version of the bitmap.
    The icon name will be used as a key in the cache
    @param iconName: filename without .png extension
    @return: QtGui.QIcon
    """
    return QIcon(getImage(iconName))


FORMATS = ['svg', 'png', 'ico']


def getPath(iconName):
    folder = FilePath(os.path.dirname(__file__))
    for fmt in FORMATS:
        path = folder.join(iconName + '.' + fmt)
        if path.exists():
            return path
    raise Exception('Icon not found: %s' % iconName)


def getImage(iconName):
    if iconName not in __iconCache:
        iconPath = getPath(iconName)
        if iconPath.hasExt('ico'):
            image = QIcon(iconPath)
        else:
            image = QPixmap(iconPath)
        if image is None or image.isNull():
            raise Exception('Icon not loaded: %s' % iconPath)
        __iconCache[iconName] = image
    else:
        image = __iconCache[iconName]
    return image
