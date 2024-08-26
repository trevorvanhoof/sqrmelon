#include "../../content/config.h"
#ifdef EIDOLON
#include "64klang2_eidolon/SynthPlayer.h"
inline void audioInit() { return _64klang2_Init(); }
inline void audioPlay() { return _64klang2_Play(); }
inline float audioCursor() { return _64klang2_GetPlaybackTime(); }
#else
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
// customized 64klang interface functions with integrated WinMM audio output
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

//api and song includes
#include "windows.h"
#include "mmsystem.h"
#include "mmreg.h"

#include "64klang/Player/Player/Synth.h"
#define INCLUDE_NODES
#include "64klang/Player/Player/64k2Patch.h"
#include "64klang/Player/Player/64k2Song.h"
#include "64klang/Player/Player/SynthAllocator.h"

//OPTIONAL: define this to add a cpu check for SSE4.1
//#define CHECK_SSE41
#ifdef CHECK_SSE41
#include <intrin.h>
#endif

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

//uninitialized data and defines
#define SAMPLE_RATE 44100
#define SAMPLE_TYPE float
SAMPLE_TYPE lpSoundBuffer[MAX_SAMPLES * 2 + 44100 * 60]; // add safety buffer for 60s 
HWAVEOUT hWaveOut;

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

//initialized data  
WAVEFORMATEX WaveFMT =
{
	WAVE_FORMAT_IEEE_FLOAT,
	2, // channels
	SAMPLE_RATE, // samples per sec
	SAMPLE_RATE * sizeof(SAMPLE_TYPE) * 2, // bytes per sec
	sizeof(SAMPLE_TYPE) * 2, // block alignment;
	sizeof(SAMPLE_TYPE) * 8, // bits per sample
	0 // extension not needed
};

WAVEHDR WaveHDR =
{
	(LPSTR)lpSoundBuffer,
	MAX_SAMPLES * sizeof(SAMPLE_TYPE) * 2,			// MAX_SAMPLES*sizeof(float)*2(stereo)
	0,
	0,
	0,
	0,
	0,
	0
};

MMTIME MMTime =
{
	TIME_SAMPLES,
	0
};

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

void audioInit()
{
	//OPTIONAL: check cpu info for sse4.1 support
#ifdef CHECK_SSE41
	int CPUInfo[4];
	__cpuid(CPUInfo, 1);
	if ((CPUInfo[2] & 0x80000) == 0)
	{
		ExitProcess(0);
	}
#endif

	// init synth and start filling the buffer 
	_64klang_Init(SynthStream, SynthNodes, SynthMonoConstantOffset, SynthStereoConstantOffset, SynthMaxOffset);
	CreateThread(0, 0, (LPTHREAD_START_ROUTINE)_64klang_Render, lpSoundBuffer, 0, 0);

	//OPTIONAL: wait a little to prefill the buffer
	//Sleep(10000);
}

void audioPlay()
{
	// start audio playback
	waveOutOpen(&hWaveOut, WAVE_MAPPER, &WaveFMT, NULL, 0, CALLBACK_NULL);
	waveOutPrepareHeader(hWaveOut, &WaveHDR, sizeof(WaveHDR));
	waveOutWrite(hWaveOut, &WaveHDR, sizeof(WaveHDR));
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

float audioCursor()
{
	waveOutGetPosition(hWaveOut, &MMTime, sizeof(MMTIME));
	return (float)(MMTime.u.sample) / 44100.0f;
}
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#endif
