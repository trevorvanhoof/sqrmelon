"""
Some python math utilities for simple types used by the UI.
"""

from math import sin, cos


def addVec3(a, b):
    return a[0] + b[0], a[1] + b[1], a[2] + b[2]


def multVec3(a, s):
    return a[0] * s, a[1] * s, a[2] * s


def rotateVec3(v, a):
    rx = (1.0, 0.0, 0.0,
          0.0, cos(a[0]), -sin(a[0]),
          0.0, sin(a[0]), cos(a[0]))

    ry = (cos(a[1]), 0.0, -sin(a[1]),
          0.0, 1.0, 0.0,
          sin(a[1]), 0.0, cos(a[1]))

    m = (rx[0] * ry[0] + rx[1] * ry[3] + rx[2] * ry[6],
         rx[0] * ry[1] + rx[1] * ry[4] + rx[2] * ry[7],
         rx[0] * ry[2] + rx[1] * ry[5] + rx[2] * ry[8],

         rx[3] * ry[0] + rx[4] * ry[3] + rx[5] * ry[6],
         rx[3] * ry[1] + rx[4] * ry[4] + rx[5] * ry[7],
         rx[3] * ry[2] + rx[4] * ry[5] + rx[5] * ry[8],

         rx[6] * ry[0] + rx[7] * ry[3] + rx[8] * ry[6],
         rx[6] * ry[1] + rx[7] * ry[4] + rx[8] * ry[7],
         rx[6] * ry[2] + rx[7] * ry[5] + rx[8] * ry[8])

    return (v[0] * m[0] + v[1] * m[3] + v[2] * m[6],
            v[0] * m[1] + v[1] * m[4] + v[2] * m[7],
            v[0] * m[2] + v[1] * m[5] + v[2] * m[8])


class Vec2(object):
    def __init__(self, x, y=None):
        if isinstance(x, Vec2):
            self.data = [x.x, x.y]
        else:
            assert isinstance(x, float) and isinstance(y, float), 'Error, invalid call to Vec2() can either be Vec2(Vec2) or Vec2(float, float)'
            self.data = [x, y]

    def __getitem__(self, i):
        return self.data[i]

    def __setitem__(self, i, v):
        self.data[i] = v

    @property
    def x(self):
        return self.data[0]

    @x.setter
    def x(self, v):
        self.data[0] = v

    @property
    def y(self):
        return self.data[1]

    @y.setter
    def y(self, v):
        self.data[1] = v

    def __neg__(self):
        return Vec2(-self.x, -self.y)

    def __add__(self, other):
        r = Vec2(self)
        r += other
        return r

    def __iadd__(self, other):
        if isinstance(other, Vec2):
            self.data[0] += other.data[0]
            self.data[1] += other.data[1]
        else:
            self.data[0] += other
            self.data[1] += other
        return self

    def __sub__(self, other):
        r = Vec2(self)
        r -= other
        return r

    def __isub__(self, other):
        if isinstance(other, Vec2):
            self.data[0] -= other.data[0]
            self.data[1] -= other.data[1]
        else:
            self.data[0] -= other
            self.data[1] -= other
        return self

    def __mul__(self, other):
        r = Vec2(self)
        r *= other
        return r

    def __imul__(self, other):
        if isinstance(other, Vec2):
            self.data[0] *= other.data[0]
            self.data[1] *= other.data[1]
        else:
            self.data[0] *= other
            self.data[1] *= other
        return self

    def __div__(self, other):
        r = Vec2(self)
        r /= other
        return r

    def __idiv__(self, other):
        if isinstance(other, Vec2):
            self.data[0] /= other.data[0]
            self.data[1] /= other.data[1]
        else:
            self.data[0] /= other
            self.data[1] /= other
        return self

    def dot(self, other):
        return self.data[0] * other.data[0] + self.data[1] * other.data[1]

    def sqrLen(self):
        return self.dot(self)

    def length(self):
        return self.sqrLen() ** 0.5

    def abs(self):
        return Vec2(abs(self.data[0]), abs(self.data[1]))

    def normalized(self):
        f = self.length()
        return self / f

    def normalize(self):
        f = self.length()
        self.__idiv__(f)

    def __repr__(self):
        return str('Vec2(%s, %s)' % (self.data[0], self.data[1]))
