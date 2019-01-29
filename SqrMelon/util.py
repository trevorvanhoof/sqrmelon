import colorsys
from fileutil import *
from xmlutil import *
from projutil import *

_randomColorSeed = 0.0


def randomColor(seed=None):
    if seed is None:
        global _randomColorSeed
        _randomColorSeed = (_randomColorSeed + 0.7) % 1.0
        r, g, b = colorsys.hsv_to_rgb(_randomColorSeed, 0.4, 0.9)
    else:
        r, g, b = colorsys.hsv_to_rgb(seed, 0.4, 0.9)
    return r * 255, g * 255, b * 255
