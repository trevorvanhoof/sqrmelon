import colorsys
from typing import Optional

_randomColorSeed = 0.0


def randomColor(seed: Optional[float] = None) -> tuple[int, int, int]:
    if seed is None:
        global _randomColorSeed
        _randomColorSeed = (_randomColorSeed + 0.7) % 1.0
        r, g, b = colorsys.hsv_to_rgb(_randomColorSeed, 0.4, 0.9)
    else:
        r, g, b = colorsys.hsv_to_rgb(seed, 0.4, 0.9)
    return int(r * 255), int(g * 255), int(b * 255)
