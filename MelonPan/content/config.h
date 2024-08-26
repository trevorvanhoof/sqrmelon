#pragma once

// Select which demo to build
// If none specified, default file names used are:
// 64k2Patch.h
// 64k2Song.h
// generated.hpp
// animationprocessor.hpp
// #define EIDOLON

// Select which audio runtime to use
// #define NO_AUDIO

// #define AUDIO_64KLANG2
// Requires winmm.lib
// Requires ole32.lib
// Requires msacm32.lib

// #define AUDIO_BASS
// Requires bass.lib

#define AUDIO_WAVESABRE
// Requires winmm.lib
// Requires msacm32.lib
// Requires dsound.lib
// TODO: WaveSabre on x86 pulls in acosf, atan2f, sinf, sqrtf; which clashes with our asm versions - can we use that mechanism across the board and get rid of the asm files?
// TODO: WaveSabre on x64 requires these math functions too but somehow they can't be found by the linker - it only finds our x64 asm versions and misses a bunch more.
// TODO: WaveSabre should officially be used by building static(?) libraries which may simplify a lot of this. Currently wavesabre_obj0.cpp just includes all the cpp files that would normally be built into those libs.
