typedef unsigned long FOURCC;
#include "WaveSabre/WaveSabreCore/include/WaveSabreCore.h"
#include "WaveSabre/WaveSabrePlayerLib/include/WaveSabrePlayerLib.h"
using namespace WaveSabrePlayerLib;
#include "../content/config.h"
#ifdef BROS_BEFORE_FOES
#include "../content/BrosBeforeFoes/Song.h"
#else
#include "../content/Song.h"
#endif

RealtimePlayer* player = nullptr;

inline void audioInit() {
    player = new RealtimePlayer(&Song, 1);
}

inline void audioPlay() {
    player->Play();
}

inline float audioCursor() {
    return (float)player->GetSongPos();
}
