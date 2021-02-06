from pycompat import *
import os, stat
from qtutil import *
from contextlib import contextmanager


class FilePath(str):
    def __new__(cls, value):
        """
        Strings are immutable, so must be constructed via new
        """
        return str.__new__(cls, value.replace('\\', '/'))

    def lower(self):
        return self.__class__(super(FilePath, self).lower())

    def upper(self):
        return self.__class__(super(FilePath, self).upper())

    def isFile(self):
        # Note, also returns false if no such file exists
        return os.path.isfile(self)

    def isDir(self):
        # Note, also returns false if no such folder exists
        return os.path.isdir(self)

    def name(self):
        """
        File name without extension
        """
        return self.__class__(os.path.splitext(os.path.basename(self))[0])

    def basename(self):
        """
        File name with extension
        """
        return self.__class__(os.path.basename(self))

    def iter(self, join=False):
        for name in os.listdir(self):
            if join:
                yield self.__class__(self.join(name))
            else:
                yield self.__class__(name)

    def abs(self):
        return self.__class__(os.path.abspath(self))

    def exists(self):
        return os.path.exists(self)

    def parent(self):
        return self.__class__(os.path.dirname(self))

    def ext(self):
        return os.path.splitext(self)[-1]

    @staticmethod
    def _prefixExt(ext):
        if ext[0] != '.':
            return '.' + ext
        return ext

    def isChildOf(self, parent):
        return parent.abs().lower().startswith(self.lower())

    def relativeTo(self, parent, assertChild=False):
        rel = self.__class__(os.path.relpath(self, parent))
        if assertChild:
            assert not rel.startswith('..')
        return rel

    def relativeToMe(self, child):
        return child.relativeTo(self)

    def stripExt(self):
        return self.ensureExt(None)

    def ensureExt(self, ext):
        if ext is None:
            return self.__class__(os.path.splitext(self)[0])
        self._prefixExt(ext)
        return self.__class__(os.path.splitext(self)[0] + self._prefixExt(ext))

    def hasExt(self, ext):
        """
        Case insensitive extension compare
        """
        return self.ext().lower() == self._prefixExt(ext).lower()

    def ensureExists(self, isFolder=False):
        """
        Create this file and the directory tree leading up to it.
        isFolder can turn this file into a folder too, not super elegant but verbose at least.
        """
        # already exists?
        if self.exists():
            return
        # create directory tree if path is supposed to be a folder
        if isFolder:
            os.makedirs(self)
            return
        else:
            # ensure parent dirs exist
            self.parent().ensureExists(True)
        # create file
        open(self, 'w').close()

    def join(self, *args):
        # type: (*Union[FilePath, str])->FilePath
        """
        join given segments to this file path
        removing prefix \\ and / of any segment
        so join('a', '/b') is the same as join('a/', 'b')
        (normal os.path trims anything before an argument with a  leading slash)

        NOTE: this replaces string.join
        """
        return self.__class__(os.path.join(self, *(a.lstrip('\\/') for a in args)))

    def __add__(self, other):
        """
        Cast concatenation
        """
        return self.__class__(super(FilePath, self).__add__(other))

    @contextmanager
    def open(self, flag='r'):
        """
        Forces a file to be readable and writable, then opens it for reading.
        """
        allFlags = stat.S_IREAD | stat.S_IWRITE | stat.S_IRGRP | stat.S_IROTH
        if self.exists() and (os.stat(self).st_mode & allFlags != allFlags):
            os.chmod(self, allFlags)
        fh = open(self, flag)
        yield fh
        fh.close()

    @contextmanager
    def edit(self, flag='w'):
        """
        Forces a file to be readable and writable, then opens it for writing.
        """
        with self.open(flag) as fh:
            yield fh

    def content(self):
        with self.open() as fh:
            return fh.read()


class FileDialog(object):
    @staticmethod
    def getSaveFileName(parent, title, startAt, text):
        res = FilePath(QFileDialog.getSaveFileName(parent, title, startAt, text))
        return None if res is None else FilePath(res)

    @staticmethod
    def getOpenFileName(parent, title, startAt, text):
        res = QFileDialog.getOpenFileName(parent, title, startAt, text)
        return None if res is None else FilePath(res)


class FileSystemWatcher(QObject):
    fileChanged = pyqtSignal(FilePath)
    directoryChanged = pyqtSignal(FilePath)

    def __init__(self):
        super(FileSystemWatcher, self).__init__()
        self.__internal = QFileSystemWatcher()
        self.__internal.fileChanged.connect(self.__forwardFileChanged)
        self.__internal.directoryChanged.connect(self.__forwardDirectoryChanged)

    def __forwardFileChanged(self, path):
        self.fileChanged.emit(FilePath(path))

    def __forwardDirectoryChanged(self, path):
        self.directoryChanged.emit(FilePath(path))

    def addPath(self, path):
        self.__internal.addPath(path)

    def addPaths(self, paths):
        self.__internal.addPaths(paths)

    def removePath(self, path):
        self.__internal.removePath(path)

    def removePaths(self, paths):
        self.__internal.removePaths(paths)
