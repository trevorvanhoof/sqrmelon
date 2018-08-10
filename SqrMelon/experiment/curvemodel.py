from qtutil import Signal
from experiment.enums import ELoopMode, ETangentMode
from experiment.modelbase import ItemRow


def sign(x): return -1 if x < 0 else 1


class HermiteKey(object):
    __slots__ = ('x', 'y', 'inTangentY', 'outTangentY', 'inTangentMode', 'outTangentMode', 'parent')

    def __init__(self, x=0.0, y=0.0, inTangentY=0.0, outTangentY=0.0, inTangentMode=ETangentMode.Custom, outTangentMode=ETangentMode.Custom, parent=None):
        self.x = x
        self.y = y
        self.inTangentY = inTangentY
        self.outTangentY = outTangentY
        self.inTangentMode = inTangentMode
        self.outTangentMode = outTangentMode
        self.parent = parent

    def setData(self, x, y, inTangentY, outTangentY, inTangentMode, outTangentMode):
        self.x = x
        self.y = y
        self.inTangentY = inTangentY
        self.outTangentY = outTangentY
        self.inTangentMode = inTangentMode
        self.outTangentMode = outTangentMode

    def copyData(self):
        return self.x, self.y, self.inTangentY, self.outTangentY, self.inTangentMode, self.outTangentMode

    def computeTangents(self):
        """
        Compute tangents based on tangent mode.
        They're left alone if tangent mode is custom, assuming the user set them to some preferred way.

        Current tangent modes:

        CUSTOM: Tangents are user defined and not computed.
        FLAT: Tangents are horizontal, causing easing in/out of keys.
        STEPPED: Special tangent value (infinity), indicating no interpolation should be done. If out- and in-tangents are both stepped for a given curve segment, the previous key value is used.
        LINEAR: Tangents are pointing to the prev / next key, causing constant velocity between keys.
        SPLINE: Given the previous and next key points, tangents are parallel to the line between these points, given a continuous feel and smoothing out acceleration. Good for (camera) angular values.
        AUTO: When velocity does not change direction acts like SPLINE, else it acts like FLAT.
        """
        inTangentDone = False
        if self.inTangentMode == ETangentMode.Custom:
            inTangentDone = True
        elif self.inTangentMode == ETangentMode.Flat:
            self.inTangentY = 0.0
            inTangentDone = True
        elif self.inTangentMode == ETangentMode.Stepped:
            self.inTangentY = float('infinity')
            inTangentDone = True

        outTangentDone = False
        if self.outTangentMode == ETangentMode.Custom:
            outTangentDone = True
        elif self.outTangentMode == ETangentMode.Flat:
            self.outTangentY = 0.0
            outTangentDone = True
        elif self.outTangentMode == ETangentMode.Stepped:
            self.outTangentY = float('infinity')
            outTangentDone = True

        # both were flat, custom or stepped, done
        if inTangentDone and outTangentDone:
            return

        keys = self.parent._keys
        idx = keys.index(self)

        if idx == 0:
            next = keys[idx + 1]
            prev = next
        elif idx == len(keys) - 1:
            prev = keys[idx - 1]
            next = prev
        else:
            prev = keys[idx - 1]
            next = keys[idx + 1]

        prevToMeDY = (self.y - prev.y) #  / (self.x - prev.x)
        meToNextDY = (next.y - self.y) #  / (next.x - self.x)

        if not inTangentDone and self.inTangentMode == ETangentMode.Linear:
            self.inTangentY = prevToMeDY
            inTangentDone = True

        if not outTangentDone and self.outTangentMode == ETangentMode.Linear:
            self.outTangentY = meToNextDY
            outTangentDone = True

        # both were flat, custom, stepped or linear, done
        if inTangentDone and outTangentDone:
            return

        splineDY = (prevToMeDY + meToNextDY) * 0.5
        autoIsSpline = sign(prevToMeDY) == sign(meToNextDY)

        if not inTangentDone:
            if self.inTangentMode == ETangentMode.Spline or autoIsSpline:
                self.inTangentY = splineDY
            else:
                assert self.inTangentMode == ETangentMode.Auto, 'Unknown tangent mode'
                self.inTangentY = 0.0

        if not outTangentDone:
            if self.outTangentMode == ETangentMode.Spline or autoIsSpline:
                self.outTangentY = splineDY
            else:
                assert self.outTangentMode == ETangentMode.Auto, 'Unknown tangent mode'
                self.outTangentY = 0.0


def binarySearch(value, data, key=lambda x: x):
    # finds value in data, assumes data is sort()ed small to large
    a, b = 0, len(data) - 1
    index = -1
    while a <= b:
        index = (a + b) / 2
        valueAtIndex = key(data[index])
        if valueAtIndex < value:
            # target is in right half
            a = index + 1
            index += 1  # in case we're done we need to insert right
        elif valueAtIndex > value:
            # target is in left half
            b = index - 1
        else:
            return index
    return index


class HermiteCurve(ItemRow):
    def __init__(self, name, loopMode=ELoopMode.Clamp, data=None):
        super(HermiteCurve, self).__init__(name, loopMode)
        self.__dict__['_keys'] = data or []
        self.__dict__['changed'] = Signal()
        for key in self._keys:
            key.parent = self

    def sort(self):
        self.__dict__['_keys'] = sorted(self.__dict__['_keys'], key=lambda x: x.x)

    def key(self, index):
        return self._keys[index]

    def keyCount(self):
        return len(self._keys)

    @property
    def keys(self):
        for key in self._keys:
            yield key

    @classmethod
    def properties(cls):
        return 'name', 'loopMode'

    def evaluate(self, x):
        # apply loop mode
        loopMode = self[1]
        if loopMode == ELoopMode.Clamp:
            # clamp it
            if x <= self._keys[0].x:
                return self._keys[0].y
            if x >= self._keys[-1].x:
                return self._keys[-1].y
        elif loopMode == ELoopMode.Loop:
            x = (x - self._keys[0].x) % (self._keys[-1].x - self._keys[0].x) + self._keys[0].x

        # find keys to interpolate
        index = binarySearch(x, self._keys, lambda key: key.x)

        # x before or exactly at first key
        if index == 0:
            return self._keys[0].y

        # x after last key this point should never be hit
        if index >= len(self._keys):
            return self._keys[-1].y

        # cubic hermite spline interpolation
        prev = self._keys[index - 1]
        next = self._keys[index]

        dx = float(next.x - prev.x)

        t = (x - prev.x) / dx

        tt = t * t
        ttt = t * tt

        tt2 = tt + tt
        tt3 = tt2 + tt
        ttt2 = ttt + ttt

        h00t = ttt2 - tt3 + 1.0
        h10t = ttt - tt2 + t
        h01t = tt3 - ttt2
        h11t = ttt - tt

        return (h00t * prev.y +
                h10t * prev.outTangentY +
                h11t * next.inTangentY +
                h01t * next.y)
