#pragma once

// Select which example/test demo to build:

// If none specified, default files used are content/...:
// - generated.hpp (sqrmelon export)
// - animationprocessor.hpp (must emulate animationprocessor.py of the project)
// - 64k2Patch.h (for 64klang2)
// - 64k2Song.h (for 64klang2)
// - Song.h (for wavesabre)
// - soundtrack.mp3 (for bass)

// Make the player more integrated with windows
#define ENABLE_WINDOWS_EVENTS

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

// Enable this to render the demo frame-by-frame, only works in Debug.
// #define EXPORT_FRAMES_FPS 60

// Enable this to print to the Output window in visual studio, only works in Debug.
// Will also save all concatenated sources as glsl files, the debug output references these by their suffixed index.
// #define USE_OUTPUT_DEBUG_STRING

// Debug where to jump into your content & how fast to run it
// Note that each shot will render at least 1 frame
#define DEBUG_START_SECONDS 0.0f
#define DEBUG_SPEED_FACTOR 1.0f
