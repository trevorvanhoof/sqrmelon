from qtutil import Signal
from experiment.enums import ELoopMode
from experiment.modelbase import ItemRow


class HermiteKey(object):
    __slots__ = ('_x', '_y', '_inTangentY', '_outTangentY')

    def __init__(self, x=0.0, y=0.0, inTangentY=0.0, outTangentY=0.0):
        self._setData(x, y, inTangentY, outTangentY)

    def copyData(self):
        return self._x, self._y, self._inTangentY, self._outTangentY

    def _setData(self, x, y, inTangentY, outTangentY):
        # type: (float, float, float, float) -> None
        self._x = x
        self._y = y
        self._inTangentY = inTangentY
        self._outTangentY = outTangentY

    def _setX(self, x):
        # type: float
        self._x = x

    def _setY(self, y):
        # type: float
        self._y = y

    def _setInTangentY(self, inTangentY):
        # type: float
        self._inTangentY = inTangentY

    def _setOutTangentY(self, outTangentY):
        # type: float
        self._outTangentY = outTangentY

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def inTangentY(self):
        return self._inTangentY

    @property
    def outTangentY(self):
        return self._outTangentY


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

    def key(self, index):
        return self._keys[index]

    def keyCount(self):
        return len(self._keys)

    @property
    def keys(self):
        for key in self._keys:
            yield key

    def addKey(self, key):
        if self._keys:
            assert self._keys[-1].x <= key.x
        self._keys.append(key)
        self.changed.emit()

    def adjustKey(self, key, data):
        key._setData(*data)
        self.changed.emit()

    def insertKey(self, index, key):
        if index < len(self._keys):
            assert key.x <= self._keys[index].x
        if 0 <= index - 1 < len(self._keys):
            assert self._keys[index - 1].x <= key.x
        self._keys.insert(index, key)
        self.changed.emit()

    def deleteKeys(self, *keys):
        for key in keys:
            self._keys.remove(key)
        self.changed.emit()

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

        # cubic hermite splien interpolation
        prev = self._keys[index - 1]
        next = self._keys[index]

        t = (x - prev.x) / float(next.x - prev.x)

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
