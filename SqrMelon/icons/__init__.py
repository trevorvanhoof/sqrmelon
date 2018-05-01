from qtutil import *
import fileutil
import os

__iconCache = {None: {}}


def get(iconName, size=48):
    """
    Retrieves an bitmap from the icon stash and
    returns a new QIcon using a cached version of the bitmap.
    The icon name will be used as a key in the cache
    @param iconName: filename without .png extension
    @return: QtGui.QIcon
    """
    return QIcon(getImage(iconName, size))


FORMATS = ['svg', 'png', 'ico']


def getPath(iconName):
    folder = os.path.dirname(__file__)
    for fmt in FORMATS:
        o = '%s/%s.%s' % (folder, iconName, fmt)
        if fileutil.exists(o):
            return o
    raise Exception('Icon not found: %s' % iconName)


def getImage(iconName, size=48):
    if not __iconCache.has_key(size):
        __iconCache[size] = {}
    if not __iconCache[size].has_key(iconName):
        try:
            iconPath = getPath('%s-%s' % (iconName, size))
        except:
            iconPath = getPath(iconName)
            size = None
        image = QPixmap(iconPath)
        if image is None or image.isNull():
            raise Exception('Icon not found: %s' % iconPath)
        __iconCache[size][iconName] = image
    else:
        image = __iconCache[size][iconName]
    return image
