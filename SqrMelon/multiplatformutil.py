import sys, os
from fileutil import FilePath
import subprocess


def platformIdentifier():
    return sys.platform.lower()


def isWindows():
    return platformIdentifier() == 'win32'


def isDarwin():
    return platformIdentifier().startswith('darwin')


def selectInFileBrowser(filePath):
    assert isinstance(filePath, FilePath)

    if isWindows():
        subprocess.Popen('explorer /select,"%s"' % filePath.abs())
        return

    try:  # elif isDarwin():
        # try if nautilus exists
        subprocess.call(('nautilus --select', str(filePath.abs())))
    except:  # else:
        # open folder instead, without selecting the file
        subprocess.call(('xdg-open', str(filePath.abs().parent())))


def openFileWithDefaultApplication(filePath):
    assert isinstance(filePath, FilePath)

    if isWindows():
        os.startfile(filePath)
    elif isDarwin():
        subprocess.call(('open', str(filePath.abs())))
    else:  # assume unknown OS has xdg-utils
        subprocess.call(('xdg-open', str(filePath.abs())))


def canValidateShaders():
    # skip shader validation step on other platforms
    return isWindows()
