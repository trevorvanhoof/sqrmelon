from __future__ import absolute_import, division, print_function
import sys

if sys.version_info.major == 2:
    class dict(dict):
        def items(self): return super(dict, self).iteritems()

        def keys(self): return super(dict, self).iterkeys()

        def values(self): return super(dict, self).itervalues()


    range = xrange
    try:
        from typing import *
    except ImportError:
        pass

if sys.version_info.major == 3:
    from typing import *

    long = int


    def execfile(path, globals=None, locals=None):
        exec(open(path).read(), globals or {}, locals or {})
