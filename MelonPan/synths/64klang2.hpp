#include "64klang2/SynthPlayer.h"

inline void audioInit() {
    return _64klang2_Init();
}

inline void audioPlay() {
    return _64klang2_Play();
}

inline float audioCursor() {
    return _64klang2_GetPlaybackTime();
}
