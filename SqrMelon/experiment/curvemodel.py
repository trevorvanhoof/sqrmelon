from experiment.enums import ELoopMode
from experiment.modelbase import ItemRow


class HermiteKey(object):
    __slots__ = ('x', 'y', 'inTangentY', 'outTangentY')

    def __init__(self, x=0.0, y=0.0, inTangentY=0.0, outTangentY=0.0):
        # type: (float, float, float, float) -> None
        self.x = x
        self.y = y
        self.inTangentY = inTangentY
        self.outTangentY = outTangentY


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
    def __init__(self, name, loopMode=ELoopMode('Clamp'), data=None):
        super(HermiteCurve, self).__init__(name, loopMode)
        self.__dict__['keys'] = data or []

    @classmethod
    def properties(cls):
        return 'name', 'loopMode'

    def evaluate(self, x):
        index = binarySearch(x, self.keys, lambda key: key.x)

        # x before first key, possibly faster to test x explicitly before binary search
        if index == 0:
            return self.keys[0].y

        # x after last key, possibly faster to test x explicitly before binary search
        if index >= len(self.keys):
            return self.keys[-1].y

        prev = self.keys[index - 1]
        next = self.keys[index]

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
