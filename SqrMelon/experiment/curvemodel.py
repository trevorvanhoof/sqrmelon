from qtutil import Signal
from experiment.enum import Enum
from experiment.modelbase import ItemRow
from experiment.util import sign


class EInsertMode(Enum):
    Error = None  # when inserting a key at another key, raise an exception
    Copy = None  # when inserting a key at another key, set the value of the exising key instead
    Passive = None  # when inserting a key at another key, silently ignore

    # Force = None  # when inserting a key at another key, insert it anyways, causing 2 keys at identical times (and undefined behaviour due to unstable sorting)

    @staticmethod
    def options():
        return 'Error', 'Copy', 'Passive'


EInsertMode.Error = EInsertMode('Error')
EInsertMode.Copy = EInsertMode('Copy')
EInsertMode.Passive = EInsertMode('Passive')


class ELoopMode(Enum):
    Clamp = None  # type: ELoopMode
    Loop = None  # type: ELoopMode

    @staticmethod
    def options():
        return 'Clamp', 'Loop'


ELoopMode.Clamp = ELoopMode('Clamp')
ELoopMode.Loop = ELoopMode('Loop')


class ETangentMode(Enum):
    Auto = None
    Flat = None
    Linear = None
    Spline = None
    Stepped = None
    Custom = None

    @staticmethod
    def options():
        return 'Auto', 'Flat', 'Linear', 'Spline', 'Stepped', 'Custom'


ETangentMode.Auto = ETangentMode('Auto')
ETangentMode.Flat = ETangentMode('Flat')
ETangentMode.Linear = ETangentMode('Linear')
ETangentMode.Spline = ETangentMode('Spline')
ETangentMode.Stepped = ETangentMode('Stepped')
ETangentMode.Custom = ETangentMode('Custom')


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

        # just 1 key, set flat and return
        if len(keys) == 1:
            self.inTangentY = 0.0
            self.outTangentY = 0.0
            return

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

        prevToMeDY = (self.y - prev.y)  # / (self.x - prev.x)
        meToNextDY = (next.y - self.y)  # / (next.x - self.x)

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
    # finds value in data, assumes data is sorted small to large
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

    def removeKeys(self, keys):
        for key in keys:
            idx = self._keys.index(key)
            self._keys.pop(idx)

            # fix tangents
            if idx > 0:
                self._keys[idx - 1].computeTangents()
            if idx < len(self._keys):
                self._keys[idx].computeTangents()

    def insertKey(self, newKey, mode=EInsertMode.Error):
        index = binarySearch(newKey.x, self._keys, lambda key: key.x)

        # prepend
        if index < 0:
            self._keys.insert(0, newKey)
            newKey.computeTangents()
            if len(self._keys) > 1:  # is there a key after?
                self._keys[1].computeTangents()
            return

        # append
        if index == len(self._keys):
            self._keys.append(newKey)
            newKey.computeTangents()
            if len(self._keys) > 1:  # is there a key before?
                self._keys[-2].computeTangents()
            return

        # overwrite
        if self._keys[index].x == newKey.x:
            cache = self._keys[index].copyData()
            if mode == EInsertMode.Error:
                raise RuntimeError()
            elif mode == EInsertMode.Copy:
                self._keys[index].y = newKey.y
            else:
                assert mode == EInsertMode.Passive, 'Unknown insertion mode %s for insertKey' % mode
            return self._keys[index], cache

        # insert
        # make sure key we are inserting before is indeed after the new key
        assert self._keys[index].x > newKey.x

        self._keys.insert(index, newKey)
        newKey.computeTangents()
        if index > 0:  # is there a key after?
            self._keys[index - 1].computeTangents()
        if index + 1 < len(self._keys):  # is there a key before?
            self._keys[index + 1].computeTangents()

    def insertKeys(self, keys):
        for key in keys:
            self.insertKey(key)

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
        # no keys, no values
        if not self._keys:
            return 0.0

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

        # x after last key, this point should never be hit
        if index >= len(self._keys):
            assert False
            return self._keys[-1].y

        # cubic hermite spline interpolation
        prev = self._keys[index - 1]
        next = self._keys[index]

        if prev.outTangentY == float('infinity'):
            return prev.y
        if next.inTangentY == float('infinity'):
            return next.y

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
