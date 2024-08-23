"""
Wrapped SIMD math library.

Regardless of the python classes wrapping & lots of if checks in initializers
this is loads faster than a python implementation + guarantees matching output with C++ code.
"""
from __future__ import annotations
import ctypes
import os
import platform
from typing import Optional, Union, Generic, TypeVar

_dllHandle: ctypes.CDLL = None # type: ignore


def prepare() -> None:
    # load the DLL once
    global _dllHandle
    if _dllHandle is not None:
        return
    if platform.architecture()[0] == '64bit':
        dllPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), r'cgmathx64.dll')
    else:
        dllPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), r'cgmathx86.dll')
    _dllHandle = ctypes.CDLL(dllPath)
    _dllHandle.Mat44_Mat44.argtypes = tuple()
    _dllHandle.Mat44_Delete.argtypes = (ctypes.c_void_p,)
    _dllHandle.Mat44_FromFloat16.argtypes = (ctypes.POINTER(ctypes.c_float),)
    _dllHandle.Mat44_Copy.argtypes = (ctypes.c_void_p,)
    _dllHandle.Mat44_Data.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_float))
    _dllHandle.Mat44_RotateX.argtypes = (ctypes.c_float,)
    _dllHandle.Mat44_RotateY.argtypes = (ctypes.c_float,)
    _dllHandle.Mat44_RotateZ.argtypes = (ctypes.c_float,)
    _dllHandle.Mat44_Translate.argtypes = (ctypes.c_float, ctypes.c_float, ctypes.c_float)
    _dllHandle.Mat44_Scale.argtypes = (ctypes.c_float, ctypes.c_float, ctypes.c_float)
    _dllHandle.Mat44_Frustum.argtypes = (ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float)
    _dllHandle.Mat44_Perspective.argtypes = (ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float)
    _dllHandle.Mat44_TRS.argtypes = (ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float)
    _dllHandle.Mat44_AxisAngle.argtypes = (ctypes.c_void_p, ctypes.c_float)
    _dllHandle.Mat44_AlignVectors.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    _dllHandle.Mat44_LookAt.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int)
    _dllHandle.Mat44_Transpose.argtypes = (ctypes.c_void_p,)
    _dllHandle.Mat44_Transpose33.argtypes = (ctypes.c_void_p,)
    _dllHandle.Mat44_Inverse.argtypes = (ctypes.c_void_p,)
    _dllHandle.Mat44_Multiply.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    _dllHandle.Mat44_IMultiply.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    _dllHandle.Mat44_Add.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    _dllHandle.Mat44_IAdd.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    _dllHandle.Mat44_AddFloat.argtypes = (ctypes.c_void_p, ctypes.c_float)
    _dllHandle.Mat44_IAddFloat.argtypes = (ctypes.c_void_p, ctypes.c_float)
    _dllHandle.Mat44_Sub.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    _dllHandle.Mat44_ISub.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    _dllHandle.Mat44_SubFloat.argtypes = (ctypes.c_void_p, ctypes.c_float)
    _dllHandle.Mat44_ISubFloat.argtypes = (ctypes.c_void_p, ctypes.c_float)
    _dllHandle.Mat44_MulFloat.argtypes = (ctypes.c_void_p, ctypes.c_float)
    _dllHandle.Mat44_IMulFloat.argtypes = (ctypes.c_void_p, ctypes.c_float)
    _dllHandle.Mat44_DivFloat.argtypes = (ctypes.c_void_p, ctypes.c_float)
    _dllHandle.Mat44_IDivFloat.argtypes = (ctypes.c_void_p, ctypes.c_float)

    _dllHandle.Mat44_Mat44.restype = ctypes.c_void_p
    _dllHandle.Mat44_Delete.restype = None
    _dllHandle.Mat44_FromFloat16.restype = ctypes.c_void_p
    _dllHandle.Mat44_Copy.restype = ctypes.c_void_p
    _dllHandle.Mat44_Data.restype = None
    _dllHandle.Mat44_RotateX.restype = ctypes.c_void_p
    _dllHandle.Mat44_RotateY.restype = ctypes.c_void_p
    _dllHandle.Mat44_RotateZ.restype = ctypes.c_void_p
    _dllHandle.Mat44_Translate.restype = ctypes.c_void_p
    _dllHandle.Mat44_Scale.restype = ctypes.c_void_p
    _dllHandle.Mat44_Frustum.restype = ctypes.c_void_p
    _dllHandle.Mat44_Perspective.restype = ctypes.c_void_p
    _dllHandle.Mat44_TRS.restype = ctypes.c_void_p
    _dllHandle.Mat44_AxisAngle.restype = ctypes.c_void_p
    _dllHandle.Mat44_AlignVectors.restype = ctypes.c_void_p
    _dllHandle.Mat44_LookAt.restype = ctypes.c_void_p
    _dllHandle.Mat44_Transpose.restype = None
    _dllHandle.Mat44_Transpose33.restype = None
    _dllHandle.Mat44_Inverse.restype = None
    _dllHandle.Mat44_Multiply.restype = ctypes.c_void_p
    _dllHandle.Mat44_IMultiply.restype = None
    _dllHandle.Mat44_Add.restype = ctypes.c_void_p
    _dllHandle.Mat44_IAdd.restype = None
    _dllHandle.Mat44_AddFloat.restype = ctypes.c_void_p
    _dllHandle.Mat44_IAddFloat.restype = None
    _dllHandle.Mat44_Sub.restype = ctypes.c_void_p
    _dllHandle.Mat44_ISub.restype = None
    _dllHandle.Mat44_SubFloat.restype = ctypes.c_void_p
    _dllHandle.Mat44_ISubFloat.restype = None
    _dllHandle.Mat44_MulFloat.restype = ctypes.c_void_p
    _dllHandle.Mat44_IMulFloat.restype = None
    _dllHandle.Mat44_DivFloat.restype = ctypes.c_void_p
    _dllHandle.Mat44_IDivFloat.restype = None

    _dllHandle.Vector_Neg.argtypes = (ctypes.c_void_p,)
    _dllHandle.Vector_Sub.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    _dllHandle.Vector_ISub.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    _dllHandle.Vector_Add.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    _dllHandle.Vector_IAdd.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    _dllHandle.Vector_Mul.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    _dllHandle.Vector_IMul.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    _dllHandle.Vector_Div.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    _dllHandle.Vector_IDiv.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    _dllHandle.Vector_SubFloat.argtypes = (ctypes.c_void_p, ctypes.c_float)
    _dllHandle.Vector_ISubFloat.argtypes = (ctypes.c_void_p, ctypes.c_float)
    _dllHandle.Vector_AddFloat.argtypes = (ctypes.c_void_p, ctypes.c_float)
    _dllHandle.Vector_IAddFloat.argtypes = (ctypes.c_void_p, ctypes.c_float)
    _dllHandle.Vector_MulFloat.argtypes = (ctypes.c_void_p, ctypes.c_float)
    _dllHandle.Vector_IMulFloat.argtypes = (ctypes.c_void_p, ctypes.c_float)
    _dllHandle.Vector_DivFloat.argtypes = (ctypes.c_void_p, ctypes.c_float)
    _dllHandle.Vector_IDivFloat.argtypes = (ctypes.c_void_p, ctypes.c_float)
    _dllHandle.Vector_Dot.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    _dllHandle.Vector_Cross.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    _dllHandle.Vector_Normalized.argtypes = (ctypes.c_void_p,)

    _dllHandle.Vector_Neg.restype = ctypes.c_void_p
    _dllHandle.Vector_Sub.restype = ctypes.c_void_p
    _dllHandle.Vector_ISub.restype = None
    _dllHandle.Vector_Add.restype = ctypes.c_void_p
    _dllHandle.Vector_IAdd.restype = None
    _dllHandle.Vector_Mul.restype = ctypes.c_void_p
    _dllHandle.Vector_IMul.restype = None
    _dllHandle.Vector_Div.restype = ctypes.c_void_p
    _dllHandle.Vector_IDiv.restype = None
    _dllHandle.Vector_SubFloat.restype = ctypes.c_void_p
    _dllHandle.Vector_ISubFloat.restype = None
    _dllHandle.Vector_AddFloat.restype = ctypes.c_void_p
    _dllHandle.Vector_IAddFloat.restype = None
    _dllHandle.Vector_MulFloat.restype = ctypes.c_void_p
    _dllHandle.Vector_IMulFloat.restype = None
    _dllHandle.Vector_DivFloat.restype = ctypes.c_void_p
    _dllHandle.Vector_IDivFloat.restype = None
    _dllHandle.Vector_Dot.restype = ctypes.c_float
    _dllHandle.Vector_Cross.restype = ctypes.c_void_p
    _dllHandle.Vector_Normalized.restype = ctypes.c_void_p

    _dllHandle.Mat44_Row.argtypes = (ctypes.c_void_p, ctypes.c_int)
    _dllHandle.Mat44_MultiplyVector.argtypes = (ctypes.c_void_p, ctypes.c_void_p)

    _dllHandle.Mat44_Row.restype = ctypes.c_void_p
    _dllHandle.Mat44_MultiplyVector.restype = ctypes.c_void_p


class Axis:
    X = 0
    Y = 1
    Z = 2
    ALL = (X, Y, Z)


T = TypeVar("T")


class VectorBase(Generic[T]):
    _size = 4

    def __init__(self, *args: Union[VectorBase, float]) -> None:
        assert self.__class__ != VectorBase, 'Instantiation of abstract class.'

        self._data: Optional[ctypes.Array[ctypes.c_float]] = None
        if args:
            if isinstance(args[0], ctypes.c_void_p):
                self._ptr = args[0]
            elif isinstance(args[0], self.__class__):
                self._ptr = _dllHandle.Vector_Copy(args[0].address())
            else:
                assert len(args) == self.__class__._size and self.__class__._size <= 4, 'Attempting to constructor vector of size {} with either wrong number of arguments {} or beyond maximum size 4.'.format(self.__class__._size, args)
                data = (ctypes.c_float * 4)(*(list(args) + [0] * (4 - self.__class__._size)))
                self._ptr = _dllHandle.Vector_FromFloat4(data)
        else:
            self._ptr = _dllHandle.Vector_Vector()

    def address(self) -> ctypes.c_void_p:
        return self._ptr

    def _fetchData(self) -> ctypes.Array[ctypes.c_float]:
        if self._data is None:
            self._data = (ctypes.c_float * 4)()
            _dllHandle.Vector_Data(self._ptr, ctypes.cast(self._data, ctypes.POINTER(ctypes.c_float)))
        return self._data

    def __getitem__(self, index: Union[int, slice]) -> float:
        data = self._fetchData()
        return data[index]

    # def __del__(self):
    #    _dllHandle.Vector_Delete(self._ptr)

    def dot(self, other: T) -> float:
        assert isinstance(other, self.__class__)
        return _dllHandle.Vector_Dot(self._ptr, other.address())

    def normalize(self) -> None:
        self._ptr = _dllHandle.Vector_Normalized(self._ptr)
        self._data = None

    def normalized(self) -> T:
        return self.__class__(_dllHandle.Vector_Normalized(self._ptr))

    def __neg__(self) -> T:
        return self.__class__(_dllHandle.Vector_Neg(self._ptr))

    def __add__(self, other: Union[T, float]) -> T:
        if isinstance(other, self.__class__):
            return self.__class__(_dllHandle.Vector_Add(self._ptr, other.address()))
        return self.__class__(_dllHandle.Vector_AddFloat(self._ptr, other))

    def __sub__(self, other: Union[T, float]) -> T:
        if isinstance(other, self.__class__):
            return self.__class__(_dllHandle.Vector_Sub(self._ptr, other.address()))
        return self.__class__(_dllHandle.Vector_SubFloat(self._ptr, other))

    def __mul__(self, other: Union[T, float, Mat44]) -> T:
        if isinstance(other, Mat44):
            return self.__class__(_dllHandle.Mat44_MultiplyVector(other.address(), self._ptr))
        if isinstance(other, self.__class__):
            return self.__class__(_dllHandle.Vector_Mul(self._ptr, other.address()))
        return self.__class__(_dllHandle.Vector_MulFloat(self._ptr, other))

    def __truediv__(self, other: Union[T, float]) -> T:
        if isinstance(other, self.__class__):
            return self.__class__(_dllHandle.Vector_Div(self._ptr, other.address()))
        return self.__class__(_dllHandle.Vector_DivFloat(self._ptr, other))

    def __iadd__(self, other: Union[T, float]) -> T:
        if isinstance(other, self.__class__):
            _dllHandle.Vector_IAdd(self._ptr, other.address())
        else:
            _dllHandle.Vector_IAddFloat(self._ptr, other)
        self._data = None
        return self

    def __isub__(self, other: Union[T, float]) -> T:
        if isinstance(other, self.__class__):
            _dllHandle.Vector_ISub(self._ptr, other.address())
        else:
            _dllHandle.Vector_IsubFloat(self._ptr, other)
        self._data = None
        return self

    def __imul__(self, other: Union[T, float, Mat44]) -> T:
        if isinstance(other, Mat44):
            ptr = _dllHandle.Mat44_MultiplyVector(other.address(), self._ptr)
            _dllHandle.Vector_Delete(self._ptr)
            self._ptr = ptr
        elif isinstance(other, self.__class__):
            _dllHandle.Vector_IMul(self._ptr, other.address())
        else:
            _dllHandle.Vector_IMulFloat(self._ptr, other)
        self._data = None
        return self

    def __idiv__(self, other: Union[T, float]) -> T:
        if isinstance(other, self.__class__):
            _dllHandle.Vector_IDiv(self._ptr, other.address())
        else:
            _dllHandle.Vector_IDivFloat(self._ptr, other)
        self._data = None
        return self


class Vec4(VectorBase["Vec4"]):
    pass


class Vec3(VectorBase["Vec3"]):
    _size = 3

    def cross(self, other: Vec3) -> Vec3:
        assert isinstance(other, Vec3)
        return Vec3(_dllHandle.Vector_Cross(self._ptr, other.address()))


class Mat44:
    def __init__(self, *args) -> None:
        self._data: Optional[ctypes.Array[ctypes.c_float]] = None
        if args:
            if isinstance(args[0], (int, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_wchar_p, ctypes.c_long)):
                self._ptr = args[0]
            elif isinstance(args[0], Mat44):
                self._ptr = _dllHandle.Mat44_Copy(args[0].address())
            else:
                data = (ctypes.c_float * 16)(*args)
                self._ptr = _dllHandle.Mat44_FromFloat16(data)
        else:
            self._ptr = _dllHandle.Mat44_Mat44()

    def address(self) -> int:
        return self._ptr

    def _fetchData(self) -> ctypes.Array[ctypes.c_float]:
        if self._data is None:
            self._data = (ctypes.c_float * 16)()
            _dllHandle.Mat44_Data(self._ptr, ctypes.cast(self._data, ctypes.POINTER(ctypes.c_float)))
        return self._data

    def __getitem__(self, index: Union[int, slice]) -> float:
        data = self._fetchData()
        return data[index]

    def __repr__(self) -> str:
        data = self._fetchData()
        return 'Mat44({:10.4f} {:10.4f} {:10.4f} {:10.4f}\n      {:10.4f} {:10.4f} {:10.4f} {:10.4f}\n      {:10.4f} {:10.4f} {:10.4f} {:10.4f}\n      {:10.4f} {:10.4f} {:10.4f} {:10.4f})'.format(*data)

    def __del__(self) -> None:
        _dllHandle.Mat44_Delete(self._ptr)

    def row(self, index: int) -> Vec4:
        # returns by reference!
        return Vec4(_dllHandle.Mat44_Row(self._ptr, index))

    def transpose(self) -> None:
        _dllHandle.Mat44_Transpose(self._ptr)
        self._data = None

    def transpose33(self) -> None:
        _dllHandle.Mat44_Transpose33(self._ptr)
        self._data = None

    def inverse(self) -> None:
        _dllHandle.Mat44_Inverse(self._ptr)
        self._data = None

    def __mul__(self, other: Union[VectorBase, Mat44, float]) -> Union[VectorBase, Mat44]:
        if isinstance(other, VectorBase):
            return other.__class__(_dllHandle.Mat44_MultiplyVector(self._ptr, other.address()))
        if isinstance(other, Mat44):
            return Mat44(_dllHandle.Mat44_Multiply(self._ptr, other.address()))
        return Mat44(_dllHandle.Mat44_MulFloat(self._ptr, other))

    def __imul__(self, other: Union[Mat44, float]) -> Mat44:
        if isinstance(other, Mat44):
            _dllHandle.Mat44_IMultiply(self._ptr, other.address())
        else:
            _dllHandle.Mat44_IMulFloat(self._ptr, other)
        self._data = None
        return self

    def __add__(self, other: Union[Mat44, float]) -> Mat44:
        if isinstance(other, Mat44):
            return Mat44(_dllHandle.Mat44_Add(self._ptr, other.address()))
        return Mat44(_dllHandle.Mat44_AddFloat(self._ptr, other))

    def __iadd__(self, other: Union[Mat44, float]) -> Mat44:
        if isinstance(other, Mat44):
            _dllHandle.Mat44_IAdd(self._ptr, other.address())
        else:
            _dllHandle.Mat44_IAddFloat(self._ptr, other)
        self._data = None
        return self

    def __sub__(self, other: Union[Mat44, float]) -> Mat44:
        if isinstance(other, Mat44):
            return Mat44(_dllHandle.Mat44_Sub(self._ptr, other.address()))
        return Mat44(_dllHandle.Mat44_SubFloat(self._ptr, other))

    def __isub__(self, other: Union[Mat44, float]) -> Mat44:
        if isinstance(other, Mat44):
            _dllHandle.Mat44_ISub(self._ptr, other.address())
        else:
            _dllHandle.Mat44_ISubFloat(self._ptr, other)
        self._data = None
        return self

    def __truediv__(self, other: float) -> Mat44:
        return Mat44(_dllHandle.Mat44_DivFloat(self._ptr, other))

    def __idiv__(self, other: float) -> Mat44:
        _dllHandle.Mat44_IDivFloat(self._ptr, other)
        self._data = None
        return self

    @staticmethod
    def rotateX(radians: float) -> Mat44:
        return Mat44(_dllHandle.Mat44_RotateX(radians))

    @staticmethod
    def rotateY(radians: float) -> Mat44:
        return Mat44(_dllHandle.Mat44_RotateY(radians))

    @staticmethod
    def rotateZ(radians: float) -> Mat44:
        return Mat44(_dllHandle.Mat44_RotateZ(radians))

    @staticmethod
    def translate(x: float, y: float, z: float) -> Mat44:
        return Mat44(_dllHandle.Mat44_Translate(x, y, z))

    @staticmethod
    def scale(x: float, y: float, z: float) -> Mat44:
        return Mat44(_dllHandle.Mat44_Scale(x, y, z))

    @staticmethod
    def perspective(fovRadians: float, aspect: float, near: float, far: float) -> Mat44:
        return Mat44(_dllHandle.Mat44_Perspective(fovRadians, aspect, near, far))

    @staticmethod
    def frustum(left: float, right: float, top: float, bottom: float, near: float, far: float) -> Mat44:
        assert near > 1e-6
        return Mat44(_dllHandle.Mat44_Frustum(left, right, top, bottom, near, far))

    @staticmethod
    def translateRotateScale(x: float = 0.0, y: float = 0.0, z: float = 0.0, rx: float = 0.0, ry: float = 0.0, rz: float = 0.0, sx: float = 1.0, sy: float = 1.0, sz: float = 1.0) -> Mat44:
        return Mat44(_dllHandle.Mat44_TRS(x, y, z, rx, ry, rz, sx, sy, sz))

    TRS = translateRotateScale

    @staticmethod
    def axisAngle(axis: Vec3, angle: float) -> Mat44:
        assert isinstance(axis, Vec3)
        return Mat44(_dllHandle.Mat44_AxisAngle(axis.address(), angle))

    @staticmethod
    def alignVectors(source: Vec3, target: Vec3) -> Mat44:
        assert isinstance(source, Vec3)
        assert isinstance(target, Vec3)
        return Mat44(_dllHandle.Mat44_AlignVectors(source.address(), target.address()))

    @staticmethod
    def lookAt(position: Vec3, target: Vec3, upDirection: Vec3, primaryAxis: int, secondaryAxis: int) -> Mat44:
        assert isinstance(position, Vec3)
        assert isinstance(target, Vec3)
        assert isinstance(upDirection, Vec3)
        assert primaryAxis in Axis.ALL
        assert secondaryAxis in Axis.ALL
        return Mat44(_dllHandle.Mat44_LookAt(position, target, upDirection, primaryAxis, secondaryAxis))
