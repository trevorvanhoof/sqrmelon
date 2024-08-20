"""
This utility outputs cProfile data as a "callgrind" cache file.

Requires pyprof2calltree:
pip install pyprof2calltree

The resulting files can be viewed using QCacheGrind for Windows:
http://sourceforge.net/projects/qcachegrindwin/

Example usage:
runctx(pythonCodeStr, globals(), locals(), executable=QCACHEGRIND)
"""
import cProfile
import os
import pstats
import subprocess
import tempfile
from typing import Optional

import pyprof2calltree

import fileutil

QCACHEGRIND = r'os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\qcachegrind074-x86\qcachegrind.exe'


def runctx(cmdstr, globals_: Optional[dict] = None, locals_: Optional[dict] = None, outpath: Optional[str] = None, executable: Optional[str] = None) -> str:
    tmp = tempfile.mktemp()
    target = tmp

    # profile to a file
    if outpath is not None:
        target = fileutil.FilePath(outpath).ensureExt('callgrind')

        # ensure out folder exists
        target.parent().ensureExists()

    # profile into out file
    cProfile.runctx(cmdstr, globals_ or {}, locals_ or {}, filename=tmp)
    pyprof2calltree.convert(pstats.Stats(tmp), target)

    # open
    if executable is not None:
        subprocess.Popen([executable, target])

    # clean up & return result
    if tmp != target:
        os.unlink(tmp)
    return target
