"""
This utility outputs cProfile data as a "callgrind" cache file.

Requires pyprof2calltree:
pip install pyprof2calltree

The resulting files can be viewed using QCacheGrind for Windows:
http://sourceforge.net/projects/qcachegrindwin/

Example usage:
runctx(pythonCodeStr, globals(), locals(), executable=QCACHEGRIND)
"""

import os
import cProfile
import tempfile
import pyprof2calltree
import pstats
import subprocess
import fileutil

QCACHEGRIND = r'os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\qcachegrind074-x86\qcachegrind.exe'


def runctx(cmdstr, globals={}, locals={}, outpath=None, executable=None):
    tmp = tempfile.mktemp()
    target = tmp

    # profile to a file
    if outpath is not None:
        target = fileutil.FilePath(outpath).ensureExt('callgrind')

        # ensure out folder exists
        target.parent().ensureExists()

    # profile into out file
    cProfile.runctx(cmdstr, globals, locals, filename=tmp)
    pyprof2calltree.convert(pstats.Stats(tmp), target)

    # open
    if executable is not None:
        subprocess.Popen([executable, target])

    # clean up & return result
    if tmp != target:
        os.unlink(tmp)
    return target
