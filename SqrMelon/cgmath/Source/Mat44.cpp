/*
CGMath by Trevor van Hoof (C) 2017

SIMD Mat44 implementation.

Row major, OpenGL style matrix support.
This means e.g. translation is stored in elements 12, 13 & 14.

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

#ifndef EXPORT
#define EXPORT
#endif

#include "Mat44.h"
#include "Vector.h"
#include <cstring>

#ifdef near
#undef near
#endif
#ifdef far
#undef far
#endif



Mat44::Mat44()
{
	memset(&data, 0, sizeof(data));
	data.elems[0] = 1;
	data.elems[5] = 1;
	data.elems[10] = 1;
	data.elems[15] = 1;
}



Mat44::Mat44(float* inData)
{
	memcpy(&data, inData, sizeof(data));
}



Mat44 Mat44::RotateX(float radians)
{
	float sa = sinf(radians);
	float ca = cosf(radians);
	float buffer[16] = { 1,0,0,0,
		0,ca,sa,0,
		0,-sa,ca,0,
		0,0,0,1 };
	return Mat44(buffer);
}



Mat44 Mat44::RotateY(float radians)
{
	float sa = sinf(radians);
	float ca = cosf(radians);
	float buffer[16] = { ca,0,-sa,0,
		0,1,0,0,
		sa,0,ca,0,
		0,0,0,1 };
	return Mat44(buffer);
}



Mat44 Mat44::RotateZ(float radians)
{
	float sa = sinf(radians);
	float ca = cosf(radians);
	float buffer[16] = { ca,sa,0,0,
		-sa,ca,0,0,
		0,0,1,0,
		0,0,0,1 };
	return Mat44(buffer);
}



Mat44 Mat44::Rotate(float radiansX, float radiansY, float radiansZ)
{
	float sx = sinf(radiansX);
	float sy = sinf(radiansY);
	float sz = sinf(radiansZ);
	float cx = cosf(radiansX);
	float cy = cosf(radiansY);
	float cz = cosf(radiansZ);
	float buffer[16] = {
		(cz*cy + sz*sx*sy), sz*cx, (cz*-sy + sz*sx*cy), 0,
		(-sz*cy + cz*sx*sy), cz*cx, (-sz*-sy + cz*sx*cy), 0,
		cx*sy, -sx, cx*cy, 0,
		0, 0, 0, 1
	};
	return Mat44(buffer);
}



Mat44 Mat44::Translate(float x, float y, float z)
{
	Mat44 res;
	res.data.elems[12] = x;
	res.data.elems[13] = y;
	res.data.elems[14] = z;
	return res;
}



Mat44 Mat44::Scale(float x, float y, float z)
{
	Mat44 res;
	res.data.elems[0] = x;
	res.data.elems[5] = y;
	res.data.elems[10] = z;
	return res;
}



Mat44 Mat44::Frustum(float left, float right, float top, float bottom, float near, float far)
{
	float A = (right + left) / (right - left);
	float B = (top + bottom) / (top - bottom);
	float C = -(far + near) / (far - near);
	float D = -(2.0f * far * near) / (far - near);
	float buffer[16] = { (2.0f * near) / (right - left), 0, A, 0, 0, -(2.0f * near) / (top - bottom), B, 0, 0, 0, C, -1, 0, 0, D, 0 };
	return Mat44(buffer);
}



Mat44 Mat44::Perspective(float fovRadians, float aspect, float near, float far)
{
	if (near < FLT_MIN)
		near = FLT_MIN;
	float fH = tanf(fovRadians * 0.5f) * near;
	float fW = fH * aspect;
	return Mat44::Frustum(-fW, fW, -fH, fH, near, far);
}



Mat44 Mat44::TRS(float x, float y, float z, float rx, float ry, float rz, float scaleX, float scaleY, float scaleZ)
{
	float sx = sinf(rx);
	float sy = sinf(ry);
	float sz = sinf(rz);
	float cx = cosf(rx);
	float cy = cosf(ry);
	float cz = cosf(rz);
	float buffer[16] = {
		scaleX*(cz*cy + sz*sx*sy), scaleX*sz*cx, scaleX*(cz*-sy + sz*sx*cy), 0,
		scaleY*(-sz*cy + cz*sx*sy), scaleY*cz*cx, scaleY*(-sz*-sy + cz*sx*cy), 0,
		scaleZ*cx*sy, scaleZ*-sx, scaleZ*cx*cy, 0,
		x, y, z, 1
	};
	return Mat44(buffer);
}



Mat44 AxisCosAngle(const __m128& axis, float cosAngle)
{
	__m128 tmp = _mm_mul_ps(axis, _mm_set_ps(1, 0, 1, 0));
	Normalized(tmp);
	
	float cz = cosAngle;
	float sz = sqrtf(1.0f - cz * cz);

	float sx = -axis.m128_f32[1];
	float cx = sqrtf(1.0f - sx * sx);
	
	float sy = tmp.m128_f32[0];
	float cy = tmp.m128_f32[2];


	float buffer[16] = {
		(cz*cy + sz*sx*sy), sz*cx, (cz*-sy + sz*sx*cy), 0,
		(-sz*cy + cz*sx*sy), cz*cx, (-sz*-sy + cz*sx*cy), 0,
		cx*sy, -sx, cx*cy, 0,
		0, 0, 0, 1
	};

	return Mat44(buffer);
}



Mat44 Mat44::AxisAngle(const __m128& axis, float angle)
{
	return AxisCosAngle(axis, cosf(angle));
}



Mat44 Mat44::AlignVectors(const __m128& source, const __m128& target)
{
	return AxisCosAngle(Cross(source, target), Dot(source, target));
}



Mat44 Mat44::LookAt(const __m128& position, const __m128& target, const __m128& upDirection, Axis primaryAxis, Axis secondaryAxis)
{
	__m128 primary = _mm_sub_ps(target, position);
	primary = Normalized(primary);

	Mat44 res;
	res[(int)primaryAxis] = primary;

	switch (primaryAxis)
	{
	case Axis::X:
		switch (secondaryAxis)
		{
		default:
		// case Axis::X: // X falls through to Y because X is already primary
		// case Axis::Y:
			res[2] = Cross(upDirection, primary);
			res[2] = Normalized(res[2]);

			res[1] = Cross(res[2], primary); // inputs are orthonormal, on post-normalization needed
			break;
		case Axis::Z:
			res[1] = Cross(primary, upDirection);
			res[1] = Normalized(res[1]);

			res[2] = Cross(res[1], primary); // inputs are orthonormal, on post-normalization needed
			break;
		}
		break;
	case Axis::Y:
		switch (secondaryAxis)
		{
		case Axis::X:
			res[2] = Cross(primary, upDirection);
			res[2] = Normalized(res[2]);


			res[0] = Cross(res[2], primary); // inputs are orthonormal, on post-normalization needed
			break;
		default:
		// case Axis::Y: // Y falls through to Z because Y is already primary
		// case Axis::Z:
			res[0] = Cross(upDirection, primary);
			res[0] = Normalized(res[0]);

			res[2] = Cross(primary, res[0]); // inputs are orthonormal, on post-normalization needed
			break;
		}
		break;
	default: // case Axis::Z:
		switch (secondaryAxis)
		{
		default: 
		// case Axis::Z: // Z falls through to X because Z is already primary
		// case Axis::X:
			res[1] = Cross(upDirection, primary);
			res[1] = Normalized(res[1]);


			res[0] = Cross(primary, res[0]); // inputs are orthonormal, on post-normalization needed
			break;
		case Axis::Y:
			res[0] = Cross(primary, upDirection);
			res[0] = Normalized(res[0]);

			res[1] = Cross(res[0], primary); // inputs are orthonormal, on post-normalization needed
			break;
		}
		break;
	}

	return res;
}



void Mat44::Transpose()
{
	_MM_TRANSPOSE4_PS(data.row0, data.row1, data.row2, data.row3);
}



void Mat44::Transpose33()
{
	float a = data.elems[1];
	data.elems[1] = data.elems[4];
	data.elems[4] = a;

	float b = data.elems[2];
	data.elems[2] = data.elems[8];
	data.elems[8] = b;

	float c = data.elems[6];
	data.elems[6] = data.elems[9];
	data.elems[9] = c;
}



void Mat44::Inverse()
{
	__m128 minor0, minor1, minor2, minor3;
	__m128 row0, row1, row2, row3;
	__m128 det, tmp1;
	tmp1 = _mm_shuffle_ps(data.row0, data.row1, _MM_SHUFFLE(1, 0, 1, 0));
	//tmp1 = _mm_loadh_pi(_mm_loadl_pi(tmp1, (__m64*)(data.elems)), (__m64*)(data.elems + 4));
	row1 = _mm_shuffle_ps(data.row2, data.row3, _MM_SHUFFLE(1, 0, 1, 0));
	//row1 = _mm_loadh_pi(_mm_loadl_pi(row1, (__m64*)(data.elems + 8)), (__m64*)(data.elems + 12));
	row0 = _mm_shuffle_ps(tmp1, row1, 0x88);
	row1 = _mm_shuffle_ps(row1, tmp1, 0xDD);
	tmp1 = _mm_loadh_pi(_mm_loadl_pi(tmp1, (__m64*)(data.elems + 2)), (__m64*)(data.elems + 6));
	row3 = _mm_shuffle_ps(data.row2, data.row3, _MM_SHUFFLE(3, 2, 3, 2));
	//row3 = _mm_loadh_pi(_mm_loadl_pi(row3, (__m64*)(data.elems + 10)), (__m64*)(data.elems + 14));
	row2 = _mm_shuffle_ps(tmp1, row3, 0x88);
	row3 = _mm_shuffle_ps(row3, tmp1, 0xDD);
	// -----------------------------------------------
	tmp1 = _mm_mul_ps(row2, row3);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0xB1);
	minor0 = _mm_mul_ps(row1, tmp1);
	minor1 = _mm_mul_ps(row0, tmp1);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0x4E);
	minor0 = _mm_sub_ps(_mm_mul_ps(row1, tmp1), minor0);
	minor1 = _mm_sub_ps(_mm_mul_ps(row0, tmp1), minor1);
	minor1 = _mm_shuffle_ps(minor1, minor1, 0x4E);
	// -----------------------------------------------
	tmp1 = _mm_mul_ps(row1, row2);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0xB1);
	minor0 = _mm_add_ps(_mm_mul_ps(row3, tmp1), minor0);
	minor3 = _mm_mul_ps(row0, tmp1);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0x4E);
	minor0 = _mm_sub_ps(minor0, _mm_mul_ps(row3, tmp1));
	minor3 = _mm_sub_ps(_mm_mul_ps(row0, tmp1), minor3);
	minor3 = _mm_shuffle_ps(minor3, minor3, 0x4E);
	// -----------------------------------------------
	tmp1 = _mm_mul_ps(_mm_shuffle_ps(row1, row1, 0x4E), row3);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0xB1);
	row2 = _mm_shuffle_ps(row2, row2, 0x4E);
	minor0 = _mm_add_ps(_mm_mul_ps(row2, tmp1), minor0);
	minor2 = _mm_mul_ps(row0, tmp1);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0x4E);
	minor0 = _mm_sub_ps(minor0, _mm_mul_ps(row2, tmp1));
	minor2 = _mm_sub_ps(_mm_mul_ps(row0, tmp1), minor2);
	minor2 = _mm_shuffle_ps(minor2, minor2, 0x4E);
	// -----------------------------------------------
	tmp1 = _mm_mul_ps(row0, row1);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0xB1);
	minor2 = _mm_add_ps(_mm_mul_ps(row3, tmp1), minor2);
	minor3 = _mm_sub_ps(_mm_mul_ps(row2, tmp1), minor3);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0x4E);
	minor2 = _mm_sub_ps(_mm_mul_ps(row3, tmp1), minor2);
	minor3 = _mm_sub_ps(minor3, _mm_mul_ps(row2, tmp1));
	// -----------------------------------------------
	tmp1 = _mm_mul_ps(row0, row3);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0xB1);
	minor1 = _mm_sub_ps(minor1, _mm_mul_ps(row2, tmp1));
	minor2 = _mm_add_ps(_mm_mul_ps(row1, tmp1), minor2);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0x4E);
	minor1 = _mm_add_ps(_mm_mul_ps(row2, tmp1), minor1);
	minor2 = _mm_sub_ps(minor2, _mm_mul_ps(row1, tmp1));
	// -----------------------------------------------
	tmp1 = _mm_mul_ps(row0, row2);
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0xB1);
	minor1 = _mm_add_ps(_mm_mul_ps(row3, tmp1), minor1);
	minor3 = _mm_sub_ps(minor3, _mm_mul_ps(row1, tmp1));
	tmp1 = _mm_shuffle_ps(tmp1, tmp1, 0x4E);
	minor1 = _mm_sub_ps(minor1, _mm_mul_ps(row3, tmp1));
	minor3 = _mm_add_ps(_mm_mul_ps(row1, tmp1), minor3);
	// -----------------------------------------------
	det = _mm_mul_ps(row0, minor0);
	det = _mm_add_ps(_mm_shuffle_ps(det, det, 0x4E), det);
	det = _mm_add_ss(_mm_shuffle_ps(det, det, 0xB1), det);
	tmp1 = _mm_rcp_ss(det);
	det = _mm_sub_ss(_mm_add_ss(tmp1, tmp1), _mm_mul_ss(det, _mm_mul_ss(tmp1, tmp1)));
	det = _mm_shuffle_ps(det, det, 0x00);
	minor0 = _mm_mul_ps(det, minor0);
	_mm_storel_pi((__m64*)(data.elems), minor0);
	_mm_storeh_pi((__m64*)(data.elems + 2), minor0);
	minor1 = _mm_mul_ps(det, minor1);
	_mm_storel_pi((__m64*)(data.elems + 4), minor1);
	_mm_storeh_pi((__m64*)(data.elems + 6), minor1);
	minor2 = _mm_mul_ps(det, minor2);
	_mm_storel_pi((__m64*)(data.elems + 8), minor2);
	_mm_storeh_pi((__m64*)(data.elems + 10), minor2);
	minor3 = _mm_mul_ps(det, minor3);
	_mm_storel_pi((__m64*)(data.elems + 12), minor3);
	_mm_storeh_pi((__m64*)(data.elems + 14), minor3);
}



Mat44 Mat44::operator*(const Mat44& other)
{
	Mat44 res = *this;
	res *= other;
	return res;
}



Mat44& Mat44::operator*=(const Mat44& other)
{
	__m128 x = _mm_shuffle_ps(data.row0, data.row0, _MM_SHUFFLE(0, 0, 0, 0));
	__m128 y = _mm_shuffle_ps(data.row0, data.row0, _MM_SHUFFLE(1, 1, 1, 1));
	__m128 z = _mm_shuffle_ps(data.row0, data.row0, _MM_SHUFFLE(2, 2, 2, 2));
	__m128 w = _mm_shuffle_ps(data.row0, data.row0, _MM_SHUFFLE(3, 3, 3, 3));
	data.row0 = _mm_add_ps(_mm_add_ps(_mm_mul_ps(x, other.data.row0),
		_mm_mul_ps(y, other.data.row1)),
		_mm_add_ps(_mm_mul_ps(z, other.data.row2),
			_mm_mul_ps(w, other.data.row3)));

	x = _mm_shuffle_ps(data.row1, data.row1, _MM_SHUFFLE(0, 0, 0, 0));
	y = _mm_shuffle_ps(data.row1, data.row1, _MM_SHUFFLE(1, 1, 1, 1));
	z = _mm_shuffle_ps(data.row1, data.row1, _MM_SHUFFLE(2, 2, 2, 2));
	w = _mm_shuffle_ps(data.row1, data.row1, _MM_SHUFFLE(3, 3, 3, 3));
	data.row1 = _mm_add_ps(_mm_add_ps(_mm_mul_ps(x, other.data.row0),
		_mm_mul_ps(y, other.data.row1)),
		_mm_add_ps(_mm_mul_ps(z, other.data.row2),
			_mm_mul_ps(w, other.data.row3)));

	x = _mm_shuffle_ps(data.row2, data.row2, _MM_SHUFFLE(0, 0, 0, 0));
	y = _mm_shuffle_ps(data.row2, data.row2, _MM_SHUFFLE(1, 1, 1, 1));
	z = _mm_shuffle_ps(data.row2, data.row2, _MM_SHUFFLE(2, 2, 2, 2));
	w = _mm_shuffle_ps(data.row2, data.row2, _MM_SHUFFLE(3, 3, 3, 3));
	data.row2 = _mm_add_ps(_mm_add_ps(_mm_mul_ps(x, other.data.row0),
		_mm_mul_ps(y, other.data.row1)),
		_mm_add_ps(_mm_mul_ps(z, other.data.row2),
			_mm_mul_ps(w, other.data.row3)));

	x = _mm_shuffle_ps(data.row3, data.row3, _MM_SHUFFLE(0, 0, 0, 0));
	y = _mm_shuffle_ps(data.row3, data.row3, _MM_SHUFFLE(1, 1, 1, 1));
	z = _mm_shuffle_ps(data.row3, data.row3, _MM_SHUFFLE(2, 2, 2, 2));
	w = _mm_shuffle_ps(data.row3, data.row3, _MM_SHUFFLE(3, 3, 3, 3));
	data.row3 = _mm_add_ps(_mm_add_ps(_mm_mul_ps(x, other.data.row0),
		_mm_mul_ps(y, other.data.row1)),
		_mm_add_ps(_mm_mul_ps(z, other.data.row2),
			_mm_mul_ps(w, other.data.row3)));

	return *this;
}



__m128 Mat44::operator*(const __m128& other) const
{
	__m128 x = _mm_shuffle_ps(other, other, _MM_SHUFFLE(0, 0, 0, 0));
	__m128 y = _mm_shuffle_ps(other, other, _MM_SHUFFLE(1, 1, 1, 1));
	__m128 z = _mm_shuffle_ps(other, other, _MM_SHUFFLE(2, 2, 2, 2));
	__m128 w = _mm_shuffle_ps(other, other, _MM_SHUFFLE(3, 3, 3, 3));

	__m128 m0 = _mm_mul_ps(data.row0, x);
	__m128 m1 = _mm_mul_ps(data.row1, y);
	__m128 m2 = _mm_mul_ps(data.row2, z);
	__m128 m3 = _mm_mul_ps(data.row3, w);

	__m128 a0 = _mm_add_ps(m0, m1);
	__m128 a1 = _mm_add_ps(m2, m3);
	__m128 a2 = _mm_add_ps(a0, a1);

	return a2;
}



const __m128& Mat44::operator[](int index) const { return data.rows[index]; }
__m128& Mat44::operator[](int index) { return data.rows[index]; }
const float& Mat44::operator()(int row, int col) const { return data.rows[row].m128_f32[col]; }
float& Mat44::operator()(int row, int col) { return data.rows[row].m128_f32[col]; }
Mat44 Mat44::operator+(const Mat44& other) { Mat44 res = *this; res += other; return res; }
Mat44& Mat44::operator+=(const Mat44& other) {
	data.row0 = _mm_add_ps(data.row0, other.data.row0);
	data.row1 = _mm_add_ps(data.row1, other.data.row1);
	data.row2 = _mm_add_ps(data.row2, other.data.row2);
	data.row3 = _mm_add_ps(data.row3, other.data.row3);
	return *this;
}
Mat44 Mat44::operator+(const float& other) { Mat44 res = *this; res += other; return res; }
Mat44& Mat44::operator+=(const float& other) {
	__m128 tmp = _mm_set_ps1(other);
	data.row0 = _mm_add_ps(data.row0, tmp);
	data.row1 = _mm_add_ps(data.row1, tmp);
	data.row2 = _mm_add_ps(data.row2, tmp);
	data.row3 = _mm_add_ps(data.row3, tmp);
	return *this;
}
Mat44 Mat44::operator-(const Mat44& other) { Mat44 res = *this; res -= other; return res; }
Mat44& Mat44::operator-=(const Mat44& other) {
	data.row0 = _mm_sub_ps(data.row0, other.data.row0);
	data.row1 = _mm_sub_ps(data.row1, other.data.row1);
	data.row2 = _mm_sub_ps(data.row2, other.data.row2);
	data.row3 = _mm_sub_ps(data.row3, other.data.row3);
	return *this;
}
Mat44 Mat44::operator-(const float& other) { Mat44 res = *this; res -= other; return res; }
Mat44& Mat44::operator-=(const float& other) {
	__m128 tmp = _mm_set_ps1(other);
	data.row0 = _mm_sub_ps(data.row0, tmp);
	data.row1 = _mm_sub_ps(data.row1, tmp);
	data.row2 = _mm_sub_ps(data.row2, tmp);
	data.row3 = _mm_sub_ps(data.row3, tmp);
	return *this;
}
Mat44 Mat44::operator*(const float& other) { Mat44 res = *this; res *= other; return res; }
Mat44& Mat44::operator*=(const float& other) {
	__m128 tmp = _mm_set_ps1(other);
	data.row0 = _mm_mul_ps(data.row0, tmp);
	data.row1 = _mm_mul_ps(data.row1, tmp);
	data.row2 = _mm_mul_ps(data.row2, tmp);
	data.row3 = _mm_mul_ps(data.row3, tmp);
	return *this;
}
Mat44 Mat44::operator/(const float& other) { Mat44 res = *this; res /= other; return res; }
Mat44& Mat44::operator/=(const float& other) {
	__m128 tmp = _mm_set_ps1(other);
	data.row0 = _mm_div_ps(data.row0, tmp);
	data.row1 = _mm_div_ps(data.row1, tmp);
	data.row2 = _mm_div_ps(data.row2, tmp);
	data.row3 = _mm_div_ps(data.row3, tmp);
	return *this;
}
bool Mat44::operator==(const Mat44& other) const { return memcmp(this, &other, sizeof(Mat44)) == 0; }
bool Mat44::operator!=(const Mat44& other) const { return !(*this == other); }



extern "C"
{
	DLL void* Mat44_Mat44() { return new Mat44; }
	DLL void Mat44_Delete(void* mat44) { delete (Mat44*)mat44; }
	DLL void* Mat44_FromFloat16(float* data) { return new Mat44(data); }
	DLL void* Mat44_Copy(void* other) { return new Mat44(*(Mat44*)other); }
	DLL void Mat44_Data(void* mat44, float* target) { memcpy(target, ((Mat44*)mat44)->data.elems, sizeof(Mat44)); }
	DLL void* Mat44_RotateX(float radians) { return new Mat44(Mat44::RotateX(radians)); }
	DLL void* Mat44_RotateY(float radians) { return new Mat44(Mat44::RotateY(radians)); }
	DLL void* Mat44_RotateZ(float radians) { return new Mat44(Mat44::RotateZ(radians)); }
	DLL void* Mat44_Translate(float x, float y, float z) { return new Mat44(Mat44::Translate(x, y, z)); }
	DLL void* Mat44_Scale(float x, float y, float z) { return new Mat44(Mat44::Scale(x, y, z)); }
	DLL void* Mat44_Frustum(float left, float right, float top, float bottom, float near, float far) { return new Mat44(Mat44::Frustum(left, right, top, bottom, near, far)); }
	DLL void* Mat44_Perspective(float fovRadians, float aspect, float near, float far) { return new Mat44(Mat44::Perspective(fovRadians, aspect, near, far)); }
	DLL void* Mat44_TRS(float x, float y, float z, float rx, float ry, float rz, float sx, float sy, float sz) { return new Mat44(Mat44::TRS(x, y, z, rx, ry, rz, sx, sy, sz)); }
	DLL void Mat44_Transpose(void* mat44) { ((Mat44*)mat44)->Transpose(); }
	DLL void Mat44_Transpose33(void* mat44) { ((Mat44*)mat44)->Transpose33(); }
	DLL void Mat44_Inverse(void* mat44) { ((Mat44*)mat44)->Inverse(); }
	DLL void* Mat44_Multiply(void* mat44, void* other) { return new Mat44(*((Mat44*)mat44) * *((Mat44*)other)); }
	DLL void Mat44_IMultiply(void* mat44, void* other) { *((Mat44*)mat44) *= *((Mat44*)other); }
	DLL void* Mat44_AxisAngle(void* axis, float angle) { return new Mat44(Mat44::AxisAngle(*(__m128*)axis, angle)); }
	DLL void* Mat44_AlignVectors(void* source, void* target) { return new Mat44(Mat44::AlignVectors(*(__m128*)source, *(__m128*)target)); }
	DLL void* Mat44_LookAt(void* position, void* target, void* upDirection, int primaryAxis, int secondaryAxis) { return new Mat44(Mat44::LookAt(*(__m128*)position, *(__m128*)target, *(__m128*)upDirection, (Axis)primaryAxis, (Axis)secondaryAxis)); }
	DLL void* Mat44_Add(void* mat44, void* other) { return new Mat44(*((Mat44*)mat44) + *((Mat44*)other)); }
	DLL void Mat44_IAdd(void* mat44, void* other) { *((Mat44*)mat44) += *((Mat44*)other); }
	DLL void* Mat44_AddFloat(void* mat44, float value) { return new Mat44(*((Mat44*)mat44) + value); }
	DLL void Mat44_IAddFloat(void* mat44, float value) { *((Mat44*)mat44) += value; }
	DLL void* Mat44_Sub(void* mat44, void* other) { return new Mat44(*((Mat44*)mat44) - *((Mat44*)other)); }
	DLL void Mat44_ISub(void* mat44, void* other) { *((Mat44*)mat44) -= *((Mat44*)other); }
	DLL void* Mat44_SubFloat(void* mat44, float value) { return new Mat44(*((Mat44*)mat44) - value); }
	DLL void Mat44_ISubFloat(void* mat44, float value) { *((Mat44*)mat44) -= value; }
	DLL void* Mat44_MulFloat(void* mat44, float value) { return new Mat44(*((Mat44*)mat44) * value); }
	DLL void Mat44_IMulFloat(void* mat44, float value) { *((Mat44*)mat44) *= value; }
	DLL void* Mat44_DivFloat(void* mat44, float value) { return new Mat44(*((Mat44*)mat44) / value); }
	DLL void Mat44_IDivFloat(void* mat44, float value) { *((Mat44*)mat44) /= value; }
	DLL void* Mat44_Row(void* mat44, int index) { return &(((Mat44*)mat44)->data.rows[index]); }
}