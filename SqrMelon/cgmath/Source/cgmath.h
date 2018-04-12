/*
CGMath by Trevor van Hoof (C) 2017

C include

Use this header to get flat functions with C-linkage support from the DLL for maximum compatibility & use from e.g. Python.
All class members are converted in <ClassName>_<FunctionName> format including constructors.
Destructors are renamed to <ClassName>_Delete.
Methods accept a pointer to an instance of the class as first argument. There is no failsafe when an invalid void* is passed in.
Memory is owned by the DLL, for garbage collected language use something like __del__ in Python or a finalizer in C# to call the appropriate delete function.

The simplest wrapper can be:
class Mat44(object):
	def __init__(self):
		self.raw = cgmath.Mat44_Mat44()
	def __del__(self):
		cgmath.Mat44_Delete(self.raw)
With the possible addition of (for automatic method searching):
	def __getattr__(self, name):
		try:
			return getattr(cgmath, '{}_{}'.format(self.__class__.__name__, name))
		except:
			return super(Mat44, self).__getattr__(name)

A more integrated looking set of wrappers using the C interface of CGMath is provided (with operator overloads & pythonic naming) in the cgmath python package.
*/

#pragma once



#ifdef EXPORT
#define DLL __declspec(dllexport)
#else
#define DLL __declspec(dllimport)
#endif



extern "C"
{
	DLL void* Mat44_Mat44();
	DLL void Mat44_Delete(void* mat44);
	DLL void* Mat44_FromFloat16(float* data);
	DLL void* Mat44_Copy(void* other);
	DLL void Mat44_Data(void* mat44, float* target);
	DLL void* Mat44_RotateX(float radians);
	DLL void* Mat44_RotateY(float radians);
	DLL void* Mat44_RotateZ(float radians);
	DLL void* Mat44_Translate(float x, float y, float z);
	DLL void* Mat44_Scale(float x, float y, float z);
	DLL void* Mat44_Frustum(float left, float right, float top, float bottom, float near, float far);
	DLL void* Mat44_Perspective(float fovRadians, float aspect, float near, float far);
	DLL void* Mat44_TRS(float x, float y, float z, float rx, float ry, float rz, float sx, float sy, float sz);
	DLL void* Mat44_AxisAngle(void* axis, float angle);
	DLL void* Mat44_AlignVectors(void* source, void* target);
	DLL void* Mat44_LookAt(void* position, void* target, void* upDirection, int primaryAxis, int secondaryAxis);
	DLL void Mat44_Transpose(void* mat44);
	DLL void Mat44_Transpose33(void* mat44); // notice this isn't faster than Tranpose()! It just allows you to inverse an orthonormal transformation matrix quite cheaply through mat.Tranpose33(); m[3] = -m.data[3];
	DLL void Mat44_Inverse(void* mat44);
	DLL void* Mat44_Multiply(void* mat44, void* other);
	DLL void Mat44_IMultiply(void* mat44, void* other);
	DLL void* Mat44_Add(void* mat44, void* other);
	DLL void Mat44_IAdd(void* mat44, void* other);
	DLL void* Mat44_AddFloat(void* mat44, float value);
	DLL void Mat44_IAddFloat(void* mat44, float value);
	DLL void* Mat44_Sub(void* mat44, void* other);
	DLL void Mat44_ISub(void* mat44, void* other);
	DLL void* Mat44_SubFloat(void* mat44, float value);
	DLL void Mat44_ISubFloat(void* mat44, float value);
	DLL void* Mat44_MulFloat(void* mat44, float value);
	DLL void Mat44_IMulFloat(void* mat44, float value);
	DLL void* Mat44_DivFloat(void* mat44, float value);
	DLL void Mat44_IDivFloat(void* mat44, float value);

	DLL void* Vector_Vector();
	DLL void Vector_Delete(void* vector);
	DLL void* Vector_FromFloat4(float* data);
	DLL void* Vector_Copy(void* other);
	DLL void Vector_Data(void* vector, float* target);
	DLL void* Vector_Neg(void* a);
	DLL void* Vector_Sub(void* a, void* b);
	DLL void Vector_ISub(void* a, void* b);
	DLL void* Vector_Add(void* a, void* b);
	DLL void Vector_IAdd(void* a, void* b);
	DLL void* Vector_Mul(void* a, void* b);
	DLL void Vector_IMul(void* a, void* b);
	DLL void* Vector_Div(void* a, void* b);
	DLL void Vector_IDiv(void* a, void* b);
	DLL void* Vector_SubFloat(void* a, float b);
	DLL void Vector_ISubFloat(void* a, float b);
	DLL void* Vector_AddFloat(void* a, float b);
	DLL void Vector_IAddFloat(void* a, float b);
	DLL void* Vector_MulFloat(void* a, float b);
	DLL void Vector_IMulFloat(void* a, float b);
	DLL void* Vector_DivFloat(void* a, float b);
	DLL void Vector_IDivFloat(void* a, float b);
	DLL float Vector_Dot(void* a, void* b);
	DLL void* Vector_Cross(void* a, void* b);
	DLL void* Vector_Normalized(void* a);

	DLL void* Mat44_Row(void* mat44, int index);
	DLL void* Mat44_MultiplyVector(void* mat44, void* vector);
}
