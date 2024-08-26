#include "bass/bass.h"

HSTREAM chan;

inline void audioInit() {}

inline void audioPlay() {
    BASS_Init(-1, 44100, 0, NULL, NULL);
    chan = BASS_StreamCreateFile(false, "audio.mp3", 0, 0, 0);
    BASS_ChannelPlay(chan, true);
}

inline float audioCursor() {
    unsigned __int64 pos = BASS_ChannelGetPosition(chan, BASS_POS_BYTE);
    return (float)BASS_ChannelBytes2Seconds(chan, pos);
}
