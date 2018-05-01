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
    if outpath is not None:
        path = os.path.splitext(outpath)[0] + '.callgrind'
        dirpath = os.path.dirname(path)
        if not fileutil.exists(dirpath):
            os.makedirs(dirpath.replace('\\', '/'))

        cProfile.runctx(cmdstr, globals, locals, filename=tmp)
        pyprof2calltree.convert(pstats.Stats(tmp), path)

        if executable is not None:
            subprocess.Popen([executable, path])
        os.unlink(tmp)
        return path

    cProfile.runctx(cmdstr, globals, locals, filename=tmp)
    pyprof2calltree.convert(pstats.Stats(tmp), tmp)
    if executable is not None:
        subprocess.Popen([executable, tmp])
    return tmp
