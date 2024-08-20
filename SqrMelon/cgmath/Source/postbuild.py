import os
import shutil

srcDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Build')
tgtDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
copyList = [
    # c dependencies
    '../cgmath.h',
    'cgmathx86.dll',
    'cgmathx64.dll',
    'cgmathx86d.dll',
    'cgmathx64d.dll',
    # c++ dependencies
    'cgmathx86.lib',
    'cgmathx64.lib',
    'cgmathx86d.lib',
    'cgmathx64d.lib',
    '../Vector.h',
    '../Mat44.h',
]
for subFile in copyList:
    shutil.copy2(os.path.join(srcDir, subFile), tgtDir)
