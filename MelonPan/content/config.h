#pragma once

// Select which demo to build
// If none specified, default files used are content/...:
// - 64k2Patch.h (for 64klang2)
// - 64k2Song.h (for 64klang2)
// - soundtrack.mp3 (for bass)
// - generated.hpp (sqrmelon export)
// - animationprocessor.hpp (must emulate animationprocessor.py of the project)
// #define EIDOLON

// Select which audio runtime to use
#define NO_AUDIO

// #define AUDIO_64KLANG2
// Requires winmm.lib
// Requires ole32.lib
// Requires msacm32.lib

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
