/*
CGMath by Trevor van Hoof (C) 2017

C++ include

Use this header to use this library as a C++ DLL.

SIMD Vec4 implementation.
Methods are first implemented as extension on the __m128 datatype,
then a Vector class is defined to wrap around this with a more object oriented interface.

The __m128 datatype is quite broad but here it is exclusively used as float[4] wrapper.
We also work around the shuffling of arguments that _mm_set_ps does, by often manually setting
the float[4] member of the struct. 

Using xmmintrin.h functions in combination with this is discouraged.
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



// Intrinsic operators made readable.
DLL __m128 operator-(const __m128& a);
DLL __m128 operator-(const __m128& a, const __m128& b);
DLL __m128& operator-=(__m128& a, const __m128& b);
DLL __m128 operator+(const __m128& a, const __m128& b);
DLL __m128& operator+=(__m128& a, const __m128& b);
DLL __m128 operator*(const __m128& a, const __m128& b);
DLL __m128& operator*=(__m128& a, const __m128& b);
DLL __m128 operator/(const __m128& a, const __m128& b);
DLL __m128& operator/=(__m128& a, const __m128& b);
DLL __m128 operator-(const __m128& a, const float& b);
DLL __m128& operator-=(__m128& a, const float& b);
DLL __m128 operator+(const __m128& a, const float& b);
DLL __m128& operator+=(__m128& a, const float& b);
DLL __m128 operator*(const __m128& a, const float& b);
DLL __m128& operator*=(__m128& a, const float& b);
DLL __m128 operator/(const __m128& a, const float& b);
DLL __m128& operator/=(__m128& a, const float& b);



// Global vector utilities.
DLL float Dot(const __m128& a, const __m128& b);
DLL __m128 Cross(const __m128& a, const __m128& b);
DLL __m128 Normalized(const __m128& a);



// Vector as class so we can create them on the heap, have a namespace for constants and make the utilities member functions.
// Heap allocation makes DLL exposing a lot more sane, although slower.
// Probably doing copies would be faster but then both this library and the user of the C interface would require to implement a struct of 16 bytes.
// TODO: why not both?
__declspec(align(16))
struct DLL Vector
{
	__m128 data; // storage

	Vector(); // default constructor, intializes data = Vector::ZERO
	Vector(float x, float y, float z, float w); // _mm_set_ps but accepting the arguments in the same order as they will be stored
	
	// implicit casts from and to __m128 for flexibility
	Vector(const __m128& data);
	operator __m128&();
	operator const __m128() const;

	// inline utilities
	float Dot(const __m128& b) const;
	__m128 Cross(const __m128& b) const; // built for vec3
	__m128 Normalized() const;

	// member accessors - warning: slow as it breaks SIMD
	const float& operator[](int index) const;
	float& operator[](int index);

	// aligned allocation
	void* operator new(size_t i);
	void operator delete(void* p);

	// globals
	static const Vector ZERO;
	static const Vector ONE;
	static const Vector NEG_ONE;
	static const Vector X;
	static const Vector Y;
	static const Vector Z;
	static const Vector W;
	static const Vector NEG_X;
	static const Vector NEG_Y;
	static const Vector NEG_Z;
	static const Vector NEG_W;
	static const Vector NOT_X;
	static const Vector NOT_Y;
	static const Vector NOT_Z;
	static const Vector NOT_W;
};
