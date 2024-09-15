#include <Windows.h>

unsigned long startTick = 0;

inline void audioInit() { }

inline void audioPlay() 
{
    startTick = GetTickCount();
}

inline float audioCursor() 
{
    if (startTick == 0) return 0.0f;
    return (float)(GetTickCount() - startTick) * 0.001f;
}
