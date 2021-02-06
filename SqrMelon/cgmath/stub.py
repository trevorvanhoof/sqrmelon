from pycompat import *
from math import sin, cos, tan, sqrt


def prepare(): pass  # stub for consistency, avoids breaking old code


class Axis(object):
    X = 0
    Y = 1
    Z = 2
    ALL = (X, Y, Z)


def Mat44_Row(data, index):
    return Vec4(data[index * 4:index * 4 + 4])


def Mat44_MultiplyVector(mat, vec):
    m0 = Vec4(Mat44_Row(mat, 0)) * vec[0]
    m1 = Vec4(Mat44_Row(mat, 1)) * vec[1]
    m2 = Vec4(Mat44_Row(mat, 2)) * vec[2]
    m3 = Vec4(Mat44_Row(mat, 3)) * vec[3]
    return m0 + m1 + m2 + m3


def Mat44_IMultiply(ioData, b):
    b0 = Mat44_Row(b, 0)
    b1 = Mat44_Row(b, 1)
    b2 = Mat44_Row(b, 2)
    b3 = Mat44_Row(b, 3)
    for i in range(4):
        x, y, z, w = ioData[i * 4:i * 4 + 4]
        ioData[i * 4:i * 4 + 4] = (b0 * x) + (b1 * y) + (b2 * z) + (b3 * w)


def Mat44_AxisCosAngle(axis, cosAngle):
    tmp = VectorBase([axis[0], 0.0, axis[2], 0.0])
    tmp.normalize()
    sx = -axis[1]
    cx = sqrt(1.0 - sx * sx)
    sy = tmp[0]
    cy = tmp[2]
    sz = sqrt(1.0 - cosAngle * cosAngle)
    cz = cosAngle
    return [
        (cz * cy + sz * sx * sy),
        sz * cx,
        (cz * -sy + sz * sx * cy),
        0.0,

        (-sz * cy + cz * sx * sy),
        cz * cx,
        (-sz * -sy + cz * sx * cy),
        0.0,

        cx * sy,
        -sx,
        cx * cy,
        0.0,

        0.0,
        0.0,
        0.0,
        1.0]


class VectorBase(object):
    _size = 4

    def __init__(self, *args):
        assert self.__class__ != VectorBase, 'Instantiation of abstract class.'

        self._data = [0.0, 0.0, 0.0, 0.0]
        if args:
            if isinstance(args[0], list):
                assert len(args[0]) == 4
                self._data = args[0]
            elif isinstance(args[0], self.__class__):
                self._data = args[0][:]
            else:
                msg = 'Attempting to constructor vector of size {} with either wrong number of arguments {} or ' \
                      'beyond maximum size 4.'.format(self.__class__._size, args)
                assert len(args) == self.__class__._size and self.__class__._size <= 4, msg
                self._data[:self.__class__._size] = args

    def __getitem__(self, key):
        return self._data[key]

    def dot(self, other):
        assert isinstance(other, self.__class__)
        return self[0] * other[0] + self[1] * other[1] + self[2] * other[2] + self[3] * other[3]

    def normalize(self):
        f = 1.0 / sqrt(self.dot(self))
        for i in range(4):
            self._data[i] /= f

    def normalized(self):
        copy = self.__class__(self)
        copy.normalize()
        return copy

    def __neg__(self):
        return self.__class__([-self._data[i] for i in range(len(self._data))])

    def __add__(self, other):
        if isinstance(other, self.__class__):
            return self.__class__([self._data[i] + other[i] for i in range(4)])
        return self.__class__([self._data[i] + other for i in range(4)])

    def __sub__(self, other):
        if isinstance(other, self.__class__):
            return self.__class__([self._data[i] - other[i] for i in range(4)])
        return self.__class__([self._data[i] - other for i in range(4)])

    def __mul__(self, other):
        if isinstance(other, Mat44):
            return self.__class__(Mat44_MultiplyVector(other, self))
        if isinstance(other, self.__class__):
            return self.__class__([self._data[i] * other[i] for i in range(4)])
        return self.__class__([self._data[i] * other for i in range(4)])

    def __div__(self, other):
        if isinstance(other, self.__class__):
            return self.__class__([self._data[i] / other[i] for i in range(4)])
        return self.__class__([self._data[i] / other for i in range(4)])

    def __iadd__(self, other):
        if isinstance(other, self.__class__):
            for i in range(4):
                self._data[i] += other[i]
        else:
            for i in range(4):
                self._data[i] += other
        self._data = None
        return self

    def __isub__(self, other):
        if isinstance(other, self.__class__):
            for i in range(4):
                self._data[i] -= other[i]
        else:
            for i in range(4):
                self._data[i] -= other
        self._data = None
        return self

    def __imul__(self, other):
        if isinstance(other, Mat44):
            res = Mat44_MultiplyVector(other, self)
            self._data = res._data
        elif isinstance(other, self.__class__):
            for i in range(4):
                self._data[i] *= other[i]
        else:
            for i in range(4):
                self._data[i] *= other
        self._data = None
        return self

    def __idiv__(self, other):
        if isinstance(other, self.__class__):
            for i in range(4):
                self._data[i] /= other[i]
        else:
            for i in range(4):
                self._data[i] /= other
        self._data = None
        return self


class Vec4(VectorBase):
    pass


class Vec3(VectorBase):
    _size = 3

    def cross(self, other):
        assert isinstance(other, Vec3)
        return Vec3(self._data[2] * other[1] - self._data[1] * other[2],
                    self._data[0] * other[2] - self._data[2] * other[0],
                    self._data[1] * other[0] - self._data[0] * other[1])


class Mat44(object):
    def __init__(self, *args):
        self._data = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
        if args:
            if isinstance(args[0], list):
                assert len(args[0]) == 16
                self._data = args[0]
            elif isinstance(args[0], Mat44):
                self._data = args[0][:]
            else:
                assert len(args) == 16
                self._data = list(args)

    def __getitem__(self, key):
        return self._data[key]

    def __repr__(self):
        return 'Mat44({:10.4f} {:10.4f} {:10.4f} {:10.4f}\n' \
               '      {:10.4f} {:10.4f} {:10.4f} {:10.4f}\n' \
               '      {:10.4f} {:10.4f} {:10.4f} {:10.4f}\n' \
               '      {:10.4f} {:10.4f} {:10.4f} {:10.4f})'.format(*self._data)

    def row(self, index):
        # returns by reference!
        raise NotImplementedError()  # can't return by reference in this stub
        # return Vec4(self._data[index * 4:index * 4 + 4])

    def transpose(self):
        cpy = self._data[:]

        self._data[1] = cpy[4]
        self._data[2] = cpy[8]
        self._data[3] = cpy[12]

        self._data[4] = cpy[1]
        self._data[6] = cpy[9]
        self._data[7] = cpy[13]

        self._data[8] = cpy[2]
        self._data[9] = cpy[6]
        self._data[11] = cpy[14]

        self._data[12] = cpy[3]
        self._data[13] = cpy[7]
        self._data[14] = cpy[11]

    def transpose33(self):
        a, b, c = self._data[1], self._data[2], self._data[6]

        self._data[1] = self._data[4]
        self._data[2] = self._data[8]
        self._data[6] = self._data[9]

        self._data[4] = a
        self._data[8] = b
        self._data[9] = c

    def inverse(self):
        raise NotImplementedError()

    def __mul__(self, other):
        if isinstance(other, VectorBase):
            return other.__class__(Mat44_MultiplyVector(self._data, other))
        if isinstance(other, Mat44):
            cpy = self._data[:]
            Mat44_IMultiply(cpy, other)
            return Mat44(cpy)
        return Mat44([self._data[i] * other for i in range(16)])

    def __imul__(self, other):
        if isinstance(other, Mat44):
            Mat44_IMultiply(self._data, other)
        else:
            for i in range(16):
                self._data[i] *= other
        return self

    def __add__(self, other):
        if isinstance(other, Mat44):
            return Mat44([self._data[i] + other[i] for i in range(16)])
        return Mat44([self._data[i] + other for i in range(16)])

    def __iadd__(self, other):
        if isinstance(other, Mat44):
            for i in range(16):
                self._data[i] += other[i]
        else:
            for i in range(16):
                self._data[i] += other
        return self

    def __sub__(self, other):
        if isinstance(other, Mat44):
            return Mat44([self._data[i] - other[i] for i in range(16)])
        return Mat44([self._data[i] - other for i in range(16)])

    def __isub__(self, other):
        if isinstance(other, Mat44):
            for i in range(16):
                self._data[i] -= other[i]
        else:
            for i in range(16):
                self._data[i] -= other
        return self

    def __div__(self, other):
        return Mat44([self._data[i] / other for i in range(16)])

    def __idiv__(self, other):
        for i in range(16):
            self._data[i] /= other
        return self

    @staticmethod
    def rotateX(radians):
        sa = sin(radians)
        ca = cos(radians)
        return Mat44([1.0, 0.0, 0.0, 0.0,
                      0.0, ca, sa, 0.0,
                      0.0, -sa, ca, 0.0,
                      0.0, 0.0, 0.0, 1.0])

    @staticmethod
    def rotateY(radians):
        sa = sin(radians)
        ca = cos(radians)
        return Mat44([ca, 0.0, -sa, 0.0,
                      0.0, 1.0, 0.0, 0.0,
                      sa, 0.0, ca, 0.0,
                      0.0, 0.0, 0.0, 1.0])

    @staticmethod
    def rotateZ(radians):
        sa = sin(radians)
        ca = cos(radians)
        return Mat44([ca, sa, 0.0, 0.0,
                      -sa, ca, 0.0, 0.0,
                      0.0, 0.0, 1.0, 0.0,
                      0.0, 0.0, 0.0, 1.0])

    @staticmethod
    def translate(x, y, z):
        return Mat44([1.0, 0.0, 0.0, 0.0,
                      0.0, 1.0, 0.0, 0.0,
                      0.0, 0.0, 1.0, 0.0,
                      x, y, z, 1.0])

    @staticmethod
    def scale(x, y, z):
        return Mat44([x, 0.0, 0.0, 0.0,
                      0.0, y, 0.0, 0.0,
                      0.0, 0.0, z, 0.0,
                      0.0, 0.0, 0.0, 1.0])

    @staticmethod
    def frustum(left, right, top, bottom, near, far):
        assert near > 1e-6
        A = (right + left) / (right - left)
        B = (top + bottom) / (top - bottom)
        C = -(far + near) / (far - near)
        D = -(2.0 * far * near) / (far - near)
        return Mat44([(2.0 * near) / (right - left), 0, A, 0,
                      0, -(2.0 * near) / (top - bottom), B, 0,
                      0, 0, C, -1.0,
                      0, 0, D, 0])

    @staticmethod
    def perspective(fovRadians, aspect, near, far):
        fH = tan(fovRadians * 0.5) * near
        fW = fH * aspect
        return Mat44.frustum(-fW, fW, -fH, fH, near, far)

    @staticmethod
    def translateRotateScale(x=0.0, y=0.0, z=0.0, rx=0.0, ry=0.0, rz=0.0, scx=1.0, scy=1.0, scz=1.0):
        sx = sin(rx)
        sy = sin(ry)
        sz = sin(rz)
        cx = cos(rx)
        cy = cos(ry)
        cz = cos(rz)
        return Mat44([
            scx * (cz * cy + sz * sx * sy), scx * sz * cx, scx * (cz * -sy + sz * sx * cy), 0.0,
            scy * (-sz * cy + cz * sx * sy), scy * cz * cx, scy * (-sz * -sy + cz * sx * cy), 0.0,
            scz * cx * sy, scz * -sx, scz * cx * cy, 0.0,
            x, y, z, 1.0])

    TRS = translateRotateScale

    @staticmethod
    def axisAngle(axis, angle):
        assert isinstance(axis, Vec3)
        return Mat44(Mat44_AxisCosAngle(axis, cos(angle)))

    @staticmethod
    def alignVectors(source, target):
        assert isinstance(source, Vec3)
        assert isinstance(target, Vec3)
        return Mat44(Mat44_AxisCosAngle(source.cross(target), source.dot(target)))

    @staticmethod
    def lookAt(position, target, upDirection, primaryAxis, secondaryAxis):
        assert isinstance(position, Vec3)
        assert isinstance(target, Vec3)
        assert isinstance(upDirection, Vec3)
        assert primaryAxis in Axis.ALL
        assert secondaryAxis in Axis.ALL
        raise NotImplementedError()
