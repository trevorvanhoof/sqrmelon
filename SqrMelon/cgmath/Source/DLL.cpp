/*
CGMath by Trevor van Hoof (C) 2017

Exports additional DLL functions.
*/

#pragma once

#ifndef EXPORT
#define EXPORT
#endif

#include "Vector.h"
#include "Mat44.h"

extern "C"
{
	DLL void* Mat44_MultiplyVector(void* mat44, void* vector) { return new Vector(*((Mat44*)mat44) * *((Vector*)vector)); }
}
