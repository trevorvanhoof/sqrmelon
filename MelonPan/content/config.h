#pragma once

// Select which demo to build
// If none specified, default files used are content/...:
// - generated.hpp (sqrmelon export)
// - animationprocessor.hpp (must emulate animationprocessor.py of the project)
// - 64k2Patch.h (for 64klang2)
// - 64k2Song.h (for 64klang2)
// - Song.h (for wavesabre)
// - soundtrack.mp3 (for bass)
// #define EIDOLON
// #define BROS_BEFORE_FOES // TODO: This crashes because Song.h seems to be from a much older version.

// Select which audio runtime to use
// #define NO_AUDIO

// #define AUDIO_64KLANG2
// Requires winmm.lib
// Requires ole32.lib
// Requires msacm32.lib

#define AUDIO_WAVESABRE // TODO: This doesn't build in release because it fails to link memset.
// Requires synths/WaveSabre_prebuilt/msvcrt.lib
// Requires synths/WaveSabre_prebuilt/WaveSabreCore.lib
// Requires dsound.lib
// Requires msacm32.lib
// Requires flagging sqrtf.asm to be excluded from the Release build.

// #define AUDIO_BASS
// #define BASS_FILE_PATH "content/soundtrack.mp3"
// Requires synths/bass/bass_x86.lib

// Select loader type
// #define NO_LOADER
// #define SMALLER_LOADER

// Make the player more integrated with windows
// #define ENABLE_WINDOWS_EVENTS

// Pop-up to select fullscreen or windowed & resolution
// #define RESOLUTION_SELECTOR

// Or hard-code fullscreen or windowed & resolution
#ifndef RESOLUTION_SELECTOR
#define IS_WINDOWED
#define DEMO_WIDTH 1920
#define DEMO_HEIGHT 1080
#endif

// Set the window title
#define WINDOW_TITLE "Made with SqrMelon"
