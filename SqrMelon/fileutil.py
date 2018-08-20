from SqrMelon.qtutil import *
import os, stat
from contextlib import contextmanager


def exists(filePath):
    return os.path.exists(filePath.replace('\\', '/'))


@contextmanager
def edit(filePath, flag='w'):
    """
    Forces a file to be writable & opens it.
    :type filePath: str
    :param str flag: IO mode, one of r(ead), w(rite), x(create), a(ppend), suffix with + for read-write, suffix with b for binary IO.
    """
    filePath = filePath.replace('\\', '/')
    if os.path.exists(filePath):
        os.chmod(filePath, stat.S_IWRITE)
    fh = open(filePath, flag)
    yield fh
    fh.close()


@contextmanager
def read(filePath, flag='r'):
    """
    Alternative to open() that enforces forward slashes.
    :type filePath: str
    :param str flag: IO mode, one of r(ead), w(rite), x(create), a(ppend), suffix with + for read-write, suffix with b for binary IO.
    """
    filePath = filePath.replace('\\', '/')
    fh = open(filePath, flag)
    yield fh
    fh.close()


def create(filePath):
    """
    Make sure the given directory tree & file exist.
    To just create a directory tree, end in a trailing slash.
    :type filePath: str
    """
    if os.path.exists(filePath):
        return
    d = os.path.dirname(filePath)
    if d and not os.path.exists(d):
        os.makedirs(d)
    if not os.path.basename(filePath):
        return
    open(filePath, 'w').close()


class FileSystemWatcher(QObject):
    fileChanged = pyqtSignal(str)
    directoryChanged = pyqtSignal(str)

    def __init__(self, *args):
        super(FileSystemWatcher, self).__init__()
        initialPaths = tuple()
        if args and hasattr(args[0], '__iter__'):
            initialPaths = args[0]
            if len(args) > 1:
                args = (args[1],)
            else:
                args = tuple()
        self.__internal = QFileSystemWatcher(*args)
        self.addPaths(initialPaths)
        self.__internal.fileChanged.connect(self.__forwardFileChanged)
        self.__internal.directoryChanged.connect(self.__forwardDirectoryChanged)

    def __forwardFileChanged(self, path):
        self.fileChanged.emit(path.replace('\\', '/'))

    def __forwardDirectoryChanged(self, path):
        self.directoryChanged.emit(path.replace('\\', '/'))

    def addPath(self, path):
        path = path.replace('\\', '/')
        self.__internal.addPath(path)

    def addPaths(self, paths):
        paths = [path.replace('\\', '/') for path in paths]
        self.__internal.addPaths(paths)

    def removePath(self, path):
        path = path.replace('\\', '/')
        self.__internal.removePath(path)

    def removePaths(self, paths):
        paths = [path.replace('\\', '/') for path in paths]
        self.__internal.removePaths(paths)
