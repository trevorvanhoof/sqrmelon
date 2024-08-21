import os
import subprocess
import sys

from fileutil import FilePath


def platformIdentifier() -> str:
    return sys.platform.lower()


def isWindows() -> bool:
    return platformIdentifier() == 'win32'


def isMac() -> bool:
    return platformIdentifier().startswith('darwin')


def selectInFileBrowser(filePath: FilePath) -> None:
    assert isinstance(filePath, FilePath)
    filePath = filePath.abs()

    if isWindows():
        # windows uses back slashes, and some commands don't support forward slashes (even when in quotes)
        subprocess.call('explorer /select,"%s"' % filePath.abs().replace('/', '\\'))
        return

    if isMac():
        # don't know how to select file in browser on mac,
        # but generic open of directory will at least open file browser at right place
        if filePath.abs().isFile():
            filePath = filePath.parent()
        subprocess.call(('open', str(filePath)))

    try:
        # try if nautilus exists
        subprocess.call(('nautilus --select', str(filePath)))
    except:  # TODO: No idea what exception subprocess returns if an app is missing; windows tries to see nautilus as a file and gives WindowsError, but we're past that here
        # if there is no nautilus, user has a custom file browser
        # but generic open of directory will at least open file browser at right place
        # TODO: should figure out how to let xdg-open tell us what the app name is and then hardcode a map of commands for the most popular browsers
        if filePath.abs().isFile():
            filePath = filePath.parent()
        subprocess.call(('xdg-open', str(filePath)))


def openFileWithDefaultApplication(filePath: FilePath) -> None:
    assert isinstance(filePath, FilePath)

    if isWindows():
        # windows uses back slashes, and some commands don't support forward slashes (even when in quotes)
        os.startfile(filePath.replace('/', '\\'))
    elif isMac():
        subprocess.call(('open', str(filePath)))
    else:  # assume unknown OS has xdg-utils
        subprocess.call(('xdg-open', str(filePath)))
