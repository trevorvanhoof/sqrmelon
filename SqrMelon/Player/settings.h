#pragma once

// NOTICE: due to the /nodefaultlib flag, #pragma comment(lib, "mylib.lib") syntax is ignored, so we must edit the release config to include (& exclude) the required dependencies manually
#define NO_AUDIO
// #define AUDIO_64KLANG2
// #define AUDIO_BASS
// #define SUPPORT_3D_TEXTURE
// #define SUPPORT_PNG
// #define AUDIO_WAVESABRE

// #define LOOP // Never stop never stopping. Only works with NO_AUDIO

#define DEMO_WIDTH 1920 // defaults to 1280
#define DEMO_HEIGHT 1080 // defaults to 720

#ifdef AUDIO_BASS
#define BPM 98
#endif

#ifdef NO_AUDIO
#define BPM 124.0f
#define START_BEAT 0.0f
#define SPEED 1.0f
#endif

const char* gWindowTitle = "Made with SqrMelon";

#define RESOLUTION_SELECTOR
