"""
Wrapped SIMD math library.

Regardless of the python classes wrapping & lot's of if checks in initializers
this is loads faster than a python implementation + guarantees matching output with C++ code.
"""
from wrapper import prepare

try:
    prepare()
    from wrapper import *
except:
    # something went wrong while loading the DLL version, load a python version instead
    print 'Warning: CGMath using pure-python fallback module.'
    from stub import *
