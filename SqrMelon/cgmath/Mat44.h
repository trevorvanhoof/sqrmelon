/*
CGMath by Trevor van Hoof (C) 2017

C++ include

Use this header to use this library as a C++ DLL.

SIMD Mat44 implementation.

Row major, OpenGL style matrix support.
This means e.g. translation is stored in elements 12, 13 & 14 and 3 orthagonal direction Vec4's can immediately by used as the rotation part of the matrix without transposing.

Matrices are pre-multiplied, for example the following OpenGL routine:
glMatrixMode(GL_MODELVIEW);
glLoadIdentity();
glRotatef(22.0f, 1.0f, 0.0f, 0.0f);
glTranslatef(0.0f, -5.0f, -10.0f);

Is replicated like so:
Mat44 modelView = Mat44::RotateX(22.0f / 180.0f * 3.1415926535879f);
modelView = Mat44::Translate(0, -5.0f, -10.0f) * mv;

For optimal performance you may therefore need to reverse operations:
Mat44 modelView = Mat44::Translate(0, -5.0f, -10.0f);
modelView *= Mat44::RotateX(22.0f / 180.0f * 3.1415926535879f);

Functions like Mat44::Rotate and Mat44::Translate maintain the order XYZ.
In legacy openGL that would be:
glRotatef(22, 1.0f, 0.0f, 0.0f);
glRotatef(45, 0.0f, 1.0f, 0.0f);
glRotatef(35, 0.0f, 0.0f, 1.0f);

Verbosely that would be:
Mat44::RotateZ(35.0f / 180.0f * 3.1415926535879f) * Mat44::RotateY(45.0f / 180.0f * 3.1415926535879f) * Mat44::RotateX(22.0f / 180.0f * 3.1415926535879f)

But an optimized implementation is found in the single call:
Mat44::Rotate(22.0f / 180.0f * 3.1415926535879f,
			  45.0f / 180.0f * 3.1415926535879f,
			  35.0f / 180.0f * 3.1415926535879f);
Here the legacy openGL order matches the argument order again.

One last notable thing is the implementation of gluPerspective in Mat44::Perspective. This should be identical in both implementation and resulting values.
E.g. 
glMatrixMode(GL_PROJECTION);
glLoadIdentity();
gluPerspective(35.0f, aspect, 0.1f, 100.0f);
GLfloat gl[16];
glGetFloatv(mode, gl);

Mat44 p = Mat44::Perspective(35.0f / 180.0f * PIf, aspect, 0.1f, 100.0f);

Here the values of gl should match p.elems (give or take a small epsilon.
*/

#pragma once

#include <math.h>
#include <float.h>
#include <xmmintrin.h>



#ifdef EXPORT
#define DLL __declspec(dllexport)
#else
#define DLL __declspec(dllimport)
#endif



enum class Axis : int
{
	X=0,
	Y=1,
	Z=2,
};



__declspec(align(16))
class DLL Mat44
{
public:
	union
	{
		__m128 rows[4];
		struct
		{
			__m128 row0;
			__m128 row1;
			__m128 row2;
			__m128 row3;
		};
		float elems[16];
	} data;

	Mat44();
	Mat44(float* data);
	static Mat44 RotateX(float radians);
	static Mat44 RotateY(float radians);
	static Mat44 RotateZ(float radians);
	static Mat44 Rotate(float radiansX, float radiansY, float radiansZ);
	static Mat44 Translate(float x, float y, float z);
	static Mat44 Scale(float x, float y, float z);
	static Mat44 Frustum(float left, float right, float top, float bottom, float near, float far);
	static Mat44 Perspective(float fovRadians, float aspect, float near, float far);
	static Mat44 TRS(float x, float y, float z, float rx, float ry, float rz, float sx, float sy, float sz);
	static Mat44 AxisAngle(const __m128& axis, float angle);
	static Mat44 AlignVectors(const __m128& source, const __m128& target);
	static Mat44 LookAt(const __m128& position, const __m128& target, const __m128& upDirection, Axis primaryAxis, Axis secondaryAxis);
	void Transpose();
	void Transpose33();
	void Inverse();
	const __m128& operator[](int index) const;
	__m128& operator[](int index);
	const float& operator()(int row, int col) const;
	float& operator()(int row, int col);
	Mat44 operator+(const Mat44& other);
	Mat44& operator+=(const Mat44& other);
	Mat44 operator+(const float& other);
	Mat44& operator+=(const float& other);
	Mat44 operator-(const Mat44& other);
	Mat44& operator-=(const Mat44& other);
	Mat44 operator-(const float& other);
	Mat44& operator-=(const float& other);
	Mat44 operator*(const Mat44& other);
	Mat44& operator*=(const Mat44& other);
	Mat44 operator*(const float& other);
	Mat44& operator*=(const float& other);
	Mat44 operator/(const float& other);
	Mat44& operator/=(const float& other);
	bool operator==(const Mat44& other) const;
	bool operator!=(const Mat44& other) const;

	__m128 operator*(const __m128& other) const;

	void* operator new(size_t i)
	{
		return _mm_malloc(i, 16);
	}

	void operator delete(void* p)
	{
		_mm_free(p);
	}
};
