/*
CGMath by Trevor van Hoof (C) 2017

SIMD Vec4 implementation.
Methods are first implemented as extension on the __m128 datatype,
then a Vector class is defined to wrap around this with a more object oriented interface.

The __m128 datatype is quite broad but here it is exclusively used as float[4] wrapper.
We also work around the shuffling of arguments that _mm_set_ps does, by often manually setting
the float[4] member of the struct. 

Using xmmintrin.h functions in combination with this is discouraged.
*/

#ifndef EXPORT
#define EXPORT
#endif

#include "Vector.h"
#include <cstring>



__m128 operator-(const __m128& a)
{
	return _mm_xor_ps(a, _mm_set_ps1(-0.f));
}



__m128 operator-(const __m128& a, const __m128& b)
{
	return _mm_sub_ps(a, b);
}



__m128& operator-=(__m128& a, const __m128& b)
{
	a = _mm_sub_ps(a, b);
	return a;
}



__m128 operator+(const __m128& a, const __m128& b)
{
	return _mm_add_ps(a, b);
}



__m128& operator+=(__m128& a, const __m128& b)
{
	a = _mm_add_ps(a, b);
	return a;
}



__m128 operator*(const __m128& a, const __m128& b)
{
	return _mm_mul_ps(a, b);
}



__m128& operator*=(__m128& a, const __m128& b)
{
	a = _mm_mul_ps(a, b);
	return a;
}



__m128 operator/(const __m128& a, const __m128& b)
{
	return _mm_div_ps(a, b);
}



__m128& operator/=(__m128& a, const __m128& b)
{
	a = _mm_div_ps(a, b);
	return a;
}



__m128 operator-(const __m128& a, const float& b)
{
	return _mm_sub_ps(a, _mm_set_ps1(b));
}



__m128& operator-=(__m128& a, const float& b)
{
	a = _mm_sub_ps(a, _mm_set_ps1(b));
	return a;
}



__m128 operator+(const __m128& a, const float& b)
{
	return _mm_add_ps(a, _mm_set_ps1(b));
}



__m128& operator+=(__m128& a, const float& b)
{
	a = _mm_add_ps(a, _mm_set_ps1(b));
	return a;
}



__m128 operator*(const __m128& a, const float& b)
{
	return _mm_mul_ps(a, _mm_set_ps1(b));
}



__m128& operator*=(__m128& a, const float& b)
{
	a = _mm_mul_ps(a, _mm_set_ps1(b));
	return a;
}



__m128 operator/(const __m128& a, const float& b)
{
	return _mm_div_ps(a, _mm_set_ps1(b));
}



__m128& operator/=(__m128& a, const float& b)
{
	a = _mm_div_ps(a, _mm_set_ps1(b));
	return a;
}



float Dot(const __m128& a, const __m128& b)
{
	__m128 tmp = _mm_mul_ps(a, b);
	return tmp.m128_f32[0] + tmp.m128_f32[1] + tmp.m128_f32[2] + tmp.m128_f32[3];
}



__m128 Cross(const __m128& a, const __m128& b)
{
	__m128 tmp = _mm_mul_ps(Vector::NOT_W, b);
	__m128 tmp1 = _mm_shuffle_ps(tmp, tmp, _MM_SHUFFLE(3, 1, 0, 2));
	__m128 tmp2 = _mm_shuffle_ps(a, a, _MM_SHUFFLE(3, 1, 0, 2));
	tmp1 = _mm_mul_ps(a, tmp1);
	tmp2 = _mm_mul_ps(b, tmp2);
	tmp = _mm_sub_ps(tmp1, tmp2);
	return _MM_SHUFFLE(tmp, tmp, _MM_SHUFFLE(3, 1, 0, 2))
}



__m128 Normalized(const __m128& a)
{
	// compute square length as vector
	__m128 tmp = _mm_mul_ps(a, a);
	__m128 tmp1 = _mm_shuffle_ps(tmp, tmp, _MM_SHUFFLE(1, 0, 3, 2));
	tmp = _mm_add_ps(tmp, tmp1);
	tmp1 = _mm_shuffle_ps(tmp, tmp, _MM_SHUFFLE(0, 1, 0, 1));
	tmp = _mm_add_ps(tmp, tmp1);
	// sqrt
	tmp = _mm_sqrt_ps(tmp);
	// divide
	return _mm_div_ps(a, tmp);
}



const Vector Vector::ZERO = _mm_set_ps1(0);
const Vector Vector::ONE = _mm_set_ps1(1);
const Vector Vector::NEG_ONE = _mm_set_ps1(-1);
const Vector Vector::W = _mm_set_ps(1, 0, 0, 0);
const Vector Vector::Z = _mm_set_ps(0, 1, 0, 0);
const Vector Vector::Y = _mm_set_ps(0, 0, 1, 0);
const Vector Vector::X = _mm_set_ps(0, 0, 0, 1);
const Vector Vector::NEG_W = _mm_set_ps(-1, 0, 0, 0);
const Vector Vector::NEG_Z = _mm_set_ps(0, -1, 0, 0);
const Vector Vector::NEG_Y = _mm_set_ps(0, 0, -1, 0);
const Vector Vector::NEG_X = _mm_set_ps(0, 0, 0, -1);
const Vector Vector::NOT_W = _mm_set_ps(0, 1, 1, 1);
const Vector Vector::NOT_Z = _mm_set_ps(1, 0, 1, 1);
const Vector Vector::NOT_Y = _mm_set_ps(1, 1, 0, 1);
const Vector Vector::NOT_X = _mm_set_ps(1, 1, 1, 0);



Vector::Vector() { data = ZERO; }


Vector::Vector(float x, float y, float z, float w) { data = _mm_set_ps(w,z,y,x); }


Vector::Vector(const __m128& data) : data(data) {}


Vector::operator __m128&() { return data; }


Vector::operator const __m128() const { return data; }



float Vector::Dot(const __m128& b) const { return ::Dot(data, b); }


__m128 Vector::Cross(const __m128& b) const { return ::Cross(data, b); }


__m128 Vector::Normalized() const { return ::Normalized(data); }



const float& Vector::operator[](int index) const { return data.m128_f32[index]; }


float& Vector::operator[](int index) { return data.m128_f32[index]; }



void* Vector::operator new(size_t i)
{
	return _mm_malloc(i, 16);
}



void Vector::operator delete(void* p)
{
	_mm_free(p);
}



extern "C"
{
	DLL void* Vector_Vector() { return new Vector; }
	DLL void Vector_Delete(void* vector) { delete (Vector*)vector; }
	DLL void* Vector_FromFloat4(float* data) { Vector* res = new Vector; memcpy(&(res->data), data, sizeof(__m128)); return res; }
	DLL void* Vector_Copy(void* other) { return new Vector(*(Vector*)other); }
	DLL void Vector_Data(void* vector, float* target) { memcpy(target, ((Vector*)vector)->data.m128_f32, sizeof(__m128)); }
	DLL void* Vector_Neg(void* a) { return new Vector(-*(Vector*)a); }
	DLL void* Vector_Sub(void* a, void* b) { return new Vector(*(Vector*)a - *(Vector*)b); }
	DLL void Vector_ISub(void* a, void* b) { *(Vector*)a -= *(Vector*)b; }
	DLL void* Vector_Add(void* a, void* b) { return new Vector(*(Vector*)a + *(Vector*)b); }
	DLL void Vector_IAdd(void* a, void* b) { *(Vector*)a += *(Vector*)b; }
	DLL void* Vector_Mul(void* a, void* b) { return new Vector(*(Vector*)a * *(Vector*)b); }
	DLL void Vector_IMul(void* a, void* b) { *(Vector*)a *= *(Vector*)b; }
	DLL void* Vector_Div(void* a, void* b) { return new Vector(*(Vector*)a / *(Vector*)b); }
	DLL void Vector_IDiv(void* a, void* b) { *(Vector*)a /= *(Vector*)b; }
	DLL void* Vector_SubFloat(void* a, float b) { return new Vector(*(Vector*)a - b); }
	DLL void Vector_ISubFloat(void* a, float b) { *(Vector*)a -= b; }
	DLL void* Vector_AddFloat(void* a, float b) { return new Vector(*(Vector*)a + b); }
	DLL void Vector_IAddFloat(void* a, float b) { *(Vector*)a += b; };
	DLL void* Vector_MulFloat(void* a, float b) { return new Vector(*(Vector*)a * b); }
	DLL void Vector_IMulFloat(void* a, float b) { *(Vector*)a *= b; };
	DLL void* Vector_DivFloat(void* a, float b) { return new Vector(*(Vector*)a / b); }
	DLL void Vector_IDivFloat(void* a, float b) { *(Vector*)a /= b; };
	DLL float Vector_Dot(void* a, void* b) { return ((Vector*)a)->Dot(*(Vector*)b); }
	DLL void* Vector_Cross(void* a, void* b) { return new Vector(((Vector*)a)->Cross(*(Vector*)b)); }
	DLL void* Vector_Normalized(void* a) { return new Vector(((Vector*)a)->Normalized()); }
}
