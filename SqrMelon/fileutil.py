import os, stat
from contextlib import contextmanager


@contextmanager
def edit(filePath, flag='w'):
    """
    Open a file for writing and forces it to be writable.
    :type filePath: str
    :param str flag: IO mode, one of r(ead), w(rite), x(create), a(ppend), suffix with + for read-write, suffix with b for binary IO.
    """
    if os.path.exists(filePath):
        os.chmod(filePath, stat.S_IWRITE)
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
