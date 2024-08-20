from __future__ import annotations

import os
import stat
from contextlib import contextmanager
from typing import BinaryIO, Iterable, Optional, Sequence, TextIO, Union

from qt import *


class FilePath(str):
    def __new__(cls, value: str) -> FilePath:
        """Strings are immutable, so must be constructed via new."""
        return str.__new__(cls, value.replace('\\', '/'))

    def lower(self) -> FilePath:
        return self.__class__(super(FilePath, self).lower())

    def upper(self) -> FilePath:
        return self.__class__(super(FilePath, self).upper())

    def isFile(self) -> bool:
        # Note, also returns false if no such file exists
        return os.path.isfile(self)

    def isDir(self) -> bool:
        # Note, also returns false if no such folder exists
        return os.path.isdir(self)

    def name(self) -> FilePath:
        """File name without extension."""
        return self.__class__(os.path.splitext(os.path.basename(self))[0])

    def basename(self) -> FilePath:
        """File name with extension."""
        return self.__class__(os.path.basename(self))

    def iter(self, join: bool = False) -> Iterable[FilePath]:
        for name in os.listdir(self):
            if join:
                yield self.__class__(self.join(name))
            else:
                yield self.__class__(name)

    def abs(self) -> FilePath:
        return self.__class__(os.path.abspath(self))

    def exists(self) -> bool:
        return os.path.exists(self)

    def parent(self) -> FilePath:
        return self.__class__(os.path.dirname(self))

    def ext(self) -> str:
        return os.path.splitext(self)[-1]

    @staticmethod
    def _prefixExt(ext: str) -> str:
        if ext[0] != '.':
            return '.' + ext
        return ext

    def isChildOf(self, parent: FilePath) -> bool:
        return parent.abs().lower().startswith(self.lower())

    def relativeTo(self, parent: str, assertChild: bool = False) -> FilePath:
        rel = self.__class__(os.path.relpath(self, parent))
        if assertChild:
            assert not rel.startswith('..')
        return rel

    def relativeToMe(self, child: FilePath) -> FilePath:
        return child.relativeTo(self)

    def stripExt(self) -> FilePath:
        return self.ensureExt(None)

    def ensureExt(self, ext: Optional[str]) -> FilePath:
        if ext is None:
            return self.__class__(os.path.splitext(self)[0])
        self._prefixExt(ext)
        return self.__class__(os.path.splitext(self)[0] + self._prefixExt(ext))

    def hasExt(self, ext: str) -> bool:
        """
        Case insensitive extension compare
        """
        return self.ext().lower() == self._prefixExt(ext).lower()

    def ensureExists(self, isFolder: bool = False) -> None:
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

    def join(self, *args: str) -> FilePath:
        """
        join given segments to this file path
        removing prefix \\ and / of any segment
        so join('a', '/b') is the same as join('a/', 'b')
        (normal os.path trims anything before an argument with a  leading slash)

        NOTE: this replaces string.join
        """
        return self.__class__(os.path.join(self, *(a.lstrip('\\/') for a in args)))

    def __add__(self, other: str):
        return self.__class__(super(FilePath, self).__add__(other))

    @contextmanager
    def _open(self, flag: str = 'r') -> Union[TextIO, BinaryIO]:
        """Forces a file to be readable and writable, then opens it for reading."""
        allFlags = stat.S_IREAD | stat.S_IWRITE | stat.S_IRGRP | stat.S_IROTH
        if self.exists() and (os.stat(self).st_mode & allFlags != allFlags):
            os.chmod(self, allFlags)
        fh = open(self, flag)
        yield fh
        fh.close()

    @contextmanager
    def read(self) -> TextIO:
        """Forces a file to be readable and writable, then opens it for writing."""
        with self._open('r') as fh:
            yield fh

    @contextmanager
    def edit(self) -> TextIO:
        """Forces a file to be readable and writable, then opens it for writing."""
        with self._open('w') as fh:
            yield fh

    @contextmanager
    def readBinary(self) -> BinaryIO:
        """Forces a file to be readable and writable, then opens it for writing."""
        with self._open('rb') as fh:
            yield fh

    @contextmanager
    def editBinary(self) -> BinaryIO:
        """Forces a file to be readable and writable, then opens it for writing."""
        with self._open('wb') as fh:
            yield fh

    def content(self) -> str:
        with self._open('r') as fh:
            return fh.read()


class FileDialog:
    @staticmethod
    def getSaveFileName(parent: Optional[QWidget], title: str, startAt: str, text: str) -> Optional[FilePath]:
        res = QFileDialog.getSaveFileName(parent, title, startAt, text)
        if res and res[0]:
            return FilePath(res[0])

    @staticmethod
    def getOpenFileName(parent: Optional[QWidget], title: str, startAt: str, text: str) -> Optional[FilePath]:
        res = QFileDialog.getOpenFileName(parent, title, startAt, text)
        if res and res[0]:
            return FilePath(res[0])


class FileSystemWatcher(QObject):
    fileChanged = Signal(FilePath)
    directoryChanged = Signal(FilePath)

    def __init__(self) -> None:
        super(FileSystemWatcher, self).__init__()
        self.__internal = QFileSystemWatcher()
        self.__internal.fileChanged.connect(self.__forwardFileChanged)
        self.__internal.directoryChanged.connect(self.__forwardDirectoryChanged)

    def __forwardFileChanged(self, path: str) -> None:
        self.fileChanged.emit(FilePath(path))

    def __forwardDirectoryChanged(self, path: str) -> None:
        self.directoryChanged.emit(FilePath(path))

    def addPath(self, path: str) -> None:
        self.__internal.addPath(path)

    def addPaths(self, paths: Sequence[str]) -> None:
        self.__internal.addPaths(paths)

    def removePath(self, path: str) -> None:
        self.__internal.removePath(path)

    def removePaths(self, paths: Sequence[str]) -> None:
        self.__internal.removePaths(paths)
