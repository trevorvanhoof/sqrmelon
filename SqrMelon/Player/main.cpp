#define _CRT_SECURE_NO_WARNINGS
#define WIN32_LEAN_AND_MEAN
#define VC_EXTRALEAN
#include "wglext.h"
#ifndef DEMO
#include <assert.h>
#else
#define assert(IGNORED)
#endif

#include "settings.h"

#include <cfloat>
#include "generated.hpp"

#ifdef AUDIO_64KLANG2
#include "64klang2/SynthPlayer.h"
#include "64klang2/SynthAllocator.h"
#include "64klang2/sample_t.h"
#endif

#ifdef AUDIO_BASS
#include "bass.h"
#pragma comment(lib, "bass.lib")
#endif

#ifdef AUDIO_WAVESABRE
#include "wavesabreplayerlib.h"
#include "wavesabrecore.h"
using namespace WaveSabrePlayerLib;
#include "music.h"
extern "C"{
	const IID GUID_NULL; 
	extern "C" int _purecall() { return 0; };
}
void* __cdecl operator new(unsigned int x) { return HeapAlloc(GetProcessHeap(), 0, x); }
void* __cdecl operator new[](unsigned int x) { return HeapAlloc(GetProcessHeap(), 0, x); }
#pragma function(memcpy)
extern "C" void* __cdecl memcpy(void* dst, const void* src, size_t count) { count--; do { ((char*)dst)[count] = ((char*)src)[count]; } while(count--); return dst; }
extern "C" __declspec(naked) void __cdecl _allshl(void)
{
	__asm {
		// Handle shifts of 64 or more bits (all get 0)
		cmp     cl, 64
		jae     short RETZERO
		// Handle shifts of between 0 and 31 bits
		cmp     cl, 32
		jae     short MORE32
		shld    edx, eax, cl
		shl     eax, cl
		ret
		// Handle shifts of between 32 and 63 bits
		MORE32 :
		mov     edx, eax
			xor     eax, eax
			and     cl, 31
			shl     edx, cl
			ret
			// return 0 in edx:eax
			RETZERO :
		xor     eax, eax
			xor     edx, edx
			ret
	}
}

void __cdecl operator delete(void* p, unsigned int x) { HeapFree(GetProcessHeap(), 0, p); }
void __cdecl operator delete(void* p) { HeapFree(GetProcessHeap(), 0, p); }
void __cdecl operator delete[](void* p) { HeapFree(GetProcessHeap(), 0, p); }
void __cdecl operator delete[](void* p, unsigned int x) { HeapFree(GetProcessHeap(), 0, p); }
#endif

#include <xmmintrin.h>

#ifndef DEMO_WIDTH
#define DEMO_WIDTH 1280
#endif
#ifndef DEMO_HEIGHT
#define DEMO_HEIGHT 720
#endif

extern "C" {int _fltused; }

const PIXELFORMATDESCRIPTOR pfd = { sizeof(PIXELFORMATDESCRIPTOR), 1, PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER, 32, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 32, 0, 0, 0, 0, 0, 0, 0 };

extern "C"
{
	extern float sinf(float);
	extern float sqrtf(float);
}
float cosf(float v) { return sinf(v + 3.14159265359f * 0.5f); }
float tanf(float v) { return sinf(v) / cosf(v); }

#ifdef SUPPORT_PNG
#ifndef _DEBUG
#define LODEPNG_NO_COMPILE_ERROR_TEXT
#endif
#include "lodepng.h"
void lodepng_cpy(void* dst, void* src, size_t size);
void loadTextureFile(unsigned int& t, const char* filename
#ifdef _DEBUG
	, HWND window
#endif
)
{
	unsigned error;
	unsigned char* image;
	size_t width, height;
	error = lodepng_decode_file(&image, &width, &height, filename, LCT_RGBA, 8);
#ifdef _DEBUG
	if (error != 0)
	{
		MessageBox(window, filename, "Error loading PNG", MB_OK);
		MessageBox(window, lodepng_error_text(error), "Error loading PNG", MB_OK);
		ExitProcess(0);
	}
#endif
	// flip vertically
	unsigned char* flipped = (unsigned char*)HeapAlloc(GetProcessHeap(), 0, width * height * 4);
	for (size_t y = 0; y < height; ++y)
		lodepng_cpy(&flipped[(height - y - 1) * width * 4], &image[y * width * 4], width * 4);
	glBindTexture(GL_TEXTURE_2D, t);
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, &flipped[0]);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	//glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP);
	//glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP);
}
#endif

#include "wglext.inc"

__declspec(align(16))
struct Mat44
{
	union
	{
		__m128 rows[4];
		struct
		{
			__m128 row0;
			__m128 row1;
			__m128 row2;
			__m128 row3;
		};
		float elems[16];
	} data;

	Mat44& operator*=(const Mat44& other)
	{
		__m128 x = _mm_shuffle_ps(data.row0, data.row0, _MM_SHUFFLE(0, 0, 0, 0));
		__m128 y = _mm_shuffle_ps(data.row0, data.row0, _MM_SHUFFLE(1, 1, 1, 1));
		__m128 z = _mm_shuffle_ps(data.row0, data.row0, _MM_SHUFFLE(2, 2, 2, 2));
		__m128 w = _mm_shuffle_ps(data.row0, data.row0, _MM_SHUFFLE(3, 3, 3, 3));
		data.row0 = _mm_add_ps(_mm_add_ps(_mm_mul_ps(x, other.data.row0),
			_mm_mul_ps(y, other.data.row1)),
			_mm_add_ps(_mm_mul_ps(z, other.data.row2),
				_mm_mul_ps(w, other.data.row3)));

		x = _mm_shuffle_ps(data.row1, data.row1, _MM_SHUFFLE(0, 0, 0, 0));
		y = _mm_shuffle_ps(data.row1, data.row1, _MM_SHUFFLE(1, 1, 1, 1));
		z = _mm_shuffle_ps(data.row1, data.row1, _MM_SHUFFLE(2, 2, 2, 2));
		w = _mm_shuffle_ps(data.row1, data.row1, _MM_SHUFFLE(3, 3, 3, 3));
		data.row1 = _mm_add_ps(_mm_add_ps(_mm_mul_ps(x, other.data.row0),
			_mm_mul_ps(y, other.data.row1)),
			_mm_add_ps(_mm_mul_ps(z, other.data.row2),
				_mm_mul_ps(w, other.data.row3)));

		x = _mm_shuffle_ps(data.row2, data.row2, _MM_SHUFFLE(0, 0, 0, 0));
		y = _mm_shuffle_ps(data.row2, data.row2, _MM_SHUFFLE(1, 1, 1, 1));
		z = _mm_shuffle_ps(data.row2, data.row2, _MM_SHUFFLE(2, 2, 2, 2));
		w = _mm_shuffle_ps(data.row2, data.row2, _MM_SHUFFLE(3, 3, 3, 3));
		data.row2 = _mm_add_ps(_mm_add_ps(_mm_mul_ps(x, other.data.row0),
			_mm_mul_ps(y, other.data.row1)),
			_mm_add_ps(_mm_mul_ps(z, other.data.row2),
				_mm_mul_ps(w, other.data.row3)));

		x = _mm_shuffle_ps(data.row3, data.row3, _MM_SHUFFLE(0, 0, 0, 0));
		y = _mm_shuffle_ps(data.row3, data.row3, _MM_SHUFFLE(1, 1, 1, 1));
		z = _mm_shuffle_ps(data.row3, data.row3, _MM_SHUFFLE(2, 2, 2, 2));
		w = _mm_shuffle_ps(data.row3, data.row3, _MM_SHUFFLE(3, 3, 3, 3));
		data.row3 = _mm_add_ps(_mm_add_ps(_mm_mul_ps(x, other.data.row0),
			_mm_mul_ps(y, other.data.row1)),
			_mm_add_ps(_mm_mul_ps(z, other.data.row2),
				_mm_mul_ps(w, other.data.row3)));

		return *this;
	}

	inline static Mat44 RotateX(float radians)
	{
		float sa = sinf(radians);
		float ca = cosf(radians);
		return { 1,0,0,0,
			0,ca,sa,0,
			0,-sa,ca,0,
			0,0,0,1 };
	}

	inline static Mat44 RotateY(float radians)
	{
		float sa = sinf(radians);
		float ca = cosf(radians);
		return { ca,0,-sa,0,
			0,1,0,0,
			sa,0,ca,0,
			0,0,0,1 };
	}

	inline static Mat44 RotateZ(float radians)
	{
		float sa = sinf(radians);
		float ca = cosf(radians);
		return { ca,sa,0,0,
			-sa,ca,0,0,
			0,0,1,0,
			0,0,0,1 };
	}
};

float uV[16] = { 0 };
float uFrustum[16];
float animData[sizeof(float) * 4 * gAnimEntriesMax];


void initUserImages(int width, int height
#ifdef _DEBUG
	, HWND window
#endif
)
{
#ifdef SUPPORT_PNG
	// load images
	glGenTextures(NUM_USER_IMAGES, gUserImages);

	int i = NUM_USER_IMAGES - 1;
	do
	{
		loadTextureFile(gUserImages[i], userImageFilePaths[i]
#ifdef _DEBUG 
			, window
#endif
		);
		TickLoader(width, height);
	} while (i--);
#endif
}

void bindUserImages(unsigned int program)
{
#ifdef SUPPORT_PNG
	// hard code to be > max inputs used in the render pipeline
	int i = NUM_USER_IMAGES - 1;
	do
	{
		glActiveTexture(GL_TEXTURE0 + USER_IMAGE_START + i);
		glBindTexture(GL_TEXTURE_2D, gUserImages[i]);
		glUniform1i(glGetUniformLocation(program, userImageUniforms[i]), USER_IMAGE_START + i);
	} while (i--);
#endif
}

bool evalDemo(float seconds, float beats, int width, int height, float deltaSeconds, bool isPrecalcStep = false)
{
	float localBeats;
	int shot = shotAtBeats(beats, localBeats);
	if (shot == -1)
		return false;
	int animOffset = gIntData[shot * 2 + gShotAnimationDataIds];
	int animEntries = gIntData[shot * 2 + gShotAnimationDataIds + 1];
	int scene = gIntData[shot + gShotScene];
	int passCursor = 0;

	// Evaluate curves & physics and store in buffer
	for (int uniformId = 0; uniformId < animEntries; ++uniformId)
	{
		int idx = animOffset + uniformId * 10;

		animData[uniformId * 4] = evalCurve(&gFloatData[gIntData[idx + gShotUniformData + 2]], gIntData[idx + gShotUniformData + 3], localBeats);
		if (gIntData[idx + gShotUniformData + 1] > 1)
			animData[uniformId * 4 + 1] = evalCurve(&gFloatData[gIntData[idx + gShotUniformData + 4]], gIntData[idx + gShotUniformData + 5], localBeats);
		if (gIntData[idx + gShotUniformData + 1] > 2)
			animData[uniformId * 4 + 2] = evalCurve(&gFloatData[gIntData[idx + gShotUniformData + 6]], gIntData[idx + gShotUniformData + 7], localBeats);
		if (gIntData[idx + gShotUniformData + 1] > 3)
			animData[uniformId * 4 + 3] = evalCurve(&gFloatData[gIntData[idx + gShotUniformData + 8]], gIntData[idx + gShotUniformData + 9], localBeats);

		// Do what python does in animationprocessor.py
		if (lstrcmpiA(gTextPool[gIntData[idx + gShotUniformData]], "uOrigin") == 0)
		{
			uV[12] = animData[uniformId * 4];
			uV[13] = animData[uniformId * 4 + 1];
			uV[14] = animData[uniformId * 4 + 2];
			uV[15] = 1.0f;
		}

		if (lstrcmpiA(gTextPool[gIntData[idx + gShotUniformData]], "uAngles") == 0)
		{
			Mat44 orient = Mat44::RotateY(-animData[uniformId * 4 + 1]);
			orient *= Mat44::RotateX(animData[uniformId * 4]);
			orient *= Mat44::RotateZ(animData[uniformId * 4 + 2]);

			uV[0] = orient.data.elems[0];
			uV[1] = orient.data.elems[1];
			uV[2] = orient.data.elems[2];

			uV[4] = orient.data.elems[4];
			uV[5] = orient.data.elems[5];
			uV[6] = orient.data.elems[6];

			uV[8] = orient.data.elems[8];
			uV[9] = orient.data.elems[9];
			uV[10] = orient.data.elems[10];
		}

		if (lstrcmpiA(gTextPool[gIntData[idx + gShotUniformData]], "uFovBias") == 0)
		{
			float tfov = tanf(animData[uniformId * 4]);
			float xfov = tfov * ((float)width / (float)height);
			uFrustum[0] = -xfov; uFrustum[1] = -tfov; uFrustum[2] = 1.0f;
			uFrustum[4] = xfov; uFrustum[5] = -tfov; uFrustum[6] = 1.0f;
			uFrustum[8] = -xfov; uFrustum[9] = tfov; uFrustum[10] = 1.0f;
			uFrustum[12] = xfov; uFrustum[13] = tfov; uFrustum[14] = 1.0f;
		}
	}

	// Render all passes
	do
	{
		int passIndex = gIntData[scene + passCursor + gScenePassIds + 1];
		if (!bindPass(passIndex, seconds, beats, width, height, isPrecalcStep))
		{
			continue;
		}
		// Forward uniform data to shader
		for (int uniformId = 0; uniformId < animEntries; ++uniformId)
		{
			int idx = animOffset + uniformId * 10;
			GLint loc = glGetUniformLocation(gPrograms[gIntData[passIndex * 2 + gPassProgramsAndTargets]], gTextPool[gIntData[idx + gShotUniformData]]);
			applyUniform(gIntData[idx + gShotUniformData + 1], loc, &animData[uniformId * 4]);
		}
		glUniformMatrix4fv(glGetUniformLocation(gPrograms[gIntData[passIndex * 2 + gPassProgramsAndTargets]], "uV"), 1, GL_FALSE, uV);
		glUniformMatrix4fv(glGetUniformLocation(gPrograms[gIntData[passIndex * 2 + gPassProgramsAndTargets]], "uFrustum"), 1, GL_FALSE, uFrustum);

#ifdef SUPPORT_PNG
		bindUserImages(gPrograms[gIntData[passIndex * 2 + gPassProgramsAndTargets]]);
#endif

		glRecti(-1, -1, 1, 1);
		// patch 3D textures
#ifdef SUPPORT_3D_TEXTURE
		if (!isPrecalcStep)
			continue;
		int frameBufferId = gIntData[passIndex * 2 + gPassProgramsAndTargets + 1] - 1;
		if (frameBufferId < 0)
			continue;
		int w = width;
		int h = height;
		widthHeight(frameBufferId, width, height, w, h);
		int is3d = gIntData[frameBufferId * gFrameBufferBlockSize + gFrameBufferData + 5];
		if (!is3d)
			continue;
		int j = 0;
		do
		{
			GLuint texture = *(gFrameBufferColorBuffers[frameBufferId] + j);

			glBindTexture(GL_TEXTURE_2D, texture);
			static float buffer[128 * 128 * 128 * 4];
			glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_FLOAT, buffer);
			glBindFramebuffer(GL_FRAMEBUFFER, 0);

			glGenTextures(1, &texture);
			*(gFrameBufferColorBuffers[frameBufferId] + j) = texture;
			glBindTexture(GL_TEXTURE_3D, texture);
			glTexImage3D(GL_TEXTURE_3D, 0, GL_RGBA32F, h, h, h, 0, GL_RGBA, GL_FLOAT, buffer);

			glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
			glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
			if (gIntData[frameBufferId * gFrameBufferBlockSize + gFrameBufferData + 4] == 0)
			{
				glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_S, GL_CLAMP);
				glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_T, GL_CLAMP);
			}
		} while (++j < gIntData[frameBufferId * gFrameBufferBlockSize + gFrameBufferData]);
#endif
	} while (++passCursor < gIntData[scene + gScenePassIds]);

	return true;
}


const char* loader = "#version 420\n\
uniform vec4 u;\
out vec3 o;\
void main()\
{\
vec2 t=(gl_FragCoord.xy*2.-u.yz)/u.z,\
q=abs(t)-vec2(.99,.1);\
float d=max(q.x,q.y);\
o=vec3(u.w)*(step(0.,-max(t.x-u.x*2.+1.,d+.01))+step(0.,.003-abs(d)));\
}";
const float loaderStep = 1.0f / (5.0f + gProgramCount);
float loaderState = 0.0f;
GLuint loaderProgram;
HDC device;

void InitLoader()
{
	loaderProgram = glCreateShaderProgramv(GL_FRAGMENT_SHADER, 1, &loader);
}

void DrawLoader(float fade, float width, float height)
{
	glBindFramebuffer(GL_FRAMEBUFFER, 0);
	glUseProgram(loaderProgram);
	glUniform4f(glGetUniformLocation(loaderProgram, "u"), loaderState, width, height, fade);
	glRecti(-1, -1, 1, 1);
	SwapBuffers(device);
}

void TickLoader(int width, int height)
{
	loaderState += loaderStep;
	DrawLoader(1.0f, (float)width, (float)height);
}

#ifdef RESOLUTION_SELECTOR
#include "Dialog.h"

int resolutionIndex;
bool isWindowed;

INT_PTR CALLBACK ConfigDialogProc(HWND hwndDlg, UINT message, WPARAM wParam, LPARAM lParam)
{
	switch (message)
	{
	case WM_INITDIALOG:
	{
		HWND hwndRes = GetDlgItem(hwndDlg, IDC_COMBORESO);

		SendMessage(hwndRes, CB_ADDSTRING, 0, (LPARAM)(LPCTSTR)"native");
		SendMessage(hwndRes, CB_ADDSTRING, 0, (LPARAM)(LPCTSTR)"1280 x 720");
		SendMessage(hwndRes, CB_ADDSTRING, 0, (LPARAM)(LPCTSTR)"1920 x 1080");

#ifdef _DEBUG
		SendMessage(hwndRes, CB_SETCURSEL, 1, 0);
		SendMessage(GetDlgItem(hwndDlg, IDC_CHECKWIN), BM_SETCHECK, BST_CHECKED, 0);
#else
		SendMessage(hwndRes, CB_SETCURSEL, 0, 0);
#endif
	}

	return true;

	case WM_COMMAND:
		switch (LOWORD(wParam))
		{

		case IDOK:
			resolutionIndex = SendMessage(GetDlgItem(hwndDlg, IDC_COMBORESO), CB_GETCURSEL, 0, 0);
			isWindowed = IsDlgButtonChecked(hwndDlg, IDC_CHECKWIN) == BST_CHECKED;

			EndDialog(hwndDlg, IDOK);
			break;

		case IDCANCEL:
			EndDialog(hwndDlg, IDCANCEL);
			break;
		}
	}

	return false;
}
#endif

void main()
{
#ifdef AUDIO_64KLANG2
	_64klang2_Init();
#endif

	HWND window;

	int width, height;

#ifdef RESOLUTION_SELECTOR
	// resolution selector
	INT_PTR result = DialogBox(GetModuleHandle(NULL), MAKEINTRESOURCE(IDD_DIALOGCONFIG), NULL, ConfigDialogProc);
	if (result != IDOK)
		return;

	switch (resolutionIndex)
	{
	case 1: // HD ready
		width = 1280;
		height = 720;
		break;
	case 2: // full HD
		width = 1920;
		height = 1080;
		break;
	default: // native
		width = GetSystemMetrics(SM_CXSCREEN);
		height = GetSystemMetrics(SM_CYSCREEN);
		isWindowed = true; // going to full screen only makes sense if we want to change the resolution of the screen
		break;
	}

	if (isWindowed)
	{
		window = CreateWindowExA(0, (LPCSTR)49177, gWindowTitle, WS_POPUP | WS_VISIBLE, 0, 0, width, height, 0, 0, 0, 0);
	}
	else
	{
		DEVMODE dmScreenSettings =
		{
			"", 0, 0, sizeof(dmScreenSettings), 0, DM_PELSWIDTH | DM_PELSHEIGHT | DM_DISPLAYFIXEDOUTPUT,
			0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, "", 0, 0, (DWORD)width, (DWORD)height, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
		};
		ChangeDisplaySettings(&dmScreenSettings, CDS_FULLSCREEN);
		window = CreateWindowExA(0, (LPCSTR)49177, gWindowTitle, WS_POPUP | WS_VISIBLE | WS_MAXIMIZE, 0, 0, 0, 0, 0, 0, 0, 0);
	}
#else
#if IS_WINDOWED || ((DEMO_WIDTH == 0) && (DEMO_HEIGHT == 0))
	window = CreateWindowExA(0, (LPCSTR)49177, gWindowTitle, WS_POPUP | WS_VISIBLE, 0, 0, DEMO_WIDTH, DEMO_HEIGHT, 0, 0, 0, 0);
#else
	DEVMODE dmScreenSettings =
	{
		"", 0, 0, sizeof(dmScreenSettings), 0, DM_PELSWIDTH | DM_PELSHEIGHT | DM_DISPLAYFIXEDOUTPUT,
		0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, "", 0, 0, DEMO_WIDTH, DEMO_HEIGHT, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
	};
	ChangeDisplaySettings(&dmScreenSettings, CDS_FULLSCREEN);
	window = CreateWindowExA(0, (LPCSTR)49177, gWindowTitle, WS_POPUP | WS_VISIBLE | WS_MAXIMIZE, 0, 0, 0, 0, 0, 0, 0, 0);
#endif
#endif

	ShowCursor(0);

	device = GetDC(window);
	SetPixelFormat(device, ChoosePixelFormat(device, &pfd), &pfd);
	wglMakeCurrent(device, wglCreateContext(device));

	RECT area;
	GetClientRect(window, &area);
	width = area.right - area.left;
	height = area.bottom - area.top;

	// requires active openGL context, device, width and height to be initialized
	InitLoader();
	DWORD start = GetTickCount();
	float opacity = 0.0f;
	do
	{
		DrawLoader(opacity, (float)width, (float)height);
		opacity = (GetTickCount() - start) * 0.004f;
	} while (opacity < 1.0f);

	TickLoader(width, height);

	// compile shaders
	initPrograms(width, height);
	// allocate frame buffers
	initFrameBuffers(width, height);
	TickLoader(width, height);
	// precalc textures
	evalDemo(0.0f, 0.0f, width, height, true);
	TickLoader(width, height);

	initUserImages(width, height
#ifdef _DEBUG
		, window
#endif
	);

#ifdef NO_AUDIO
	start = GetTickCount();
#endif

#ifdef AUDIO_64KLANG2
	float BPM = _64klang2_GetBPM();
	_64klang2_Play();
#endif

#ifdef AUDIO_BASS
	BASS_Init(-1, 44100, 0, NULL, NULL);
	HSTREAM chan = BASS_StreamCreateFile(false, "audio.mp3", 0, 0, 0);
	BASS_ChannelPlay(chan, true);
#endif
	
#ifdef AUDIO_WAVESABRE
	WaveSabrePlayerLib::RealtimePlayer player(&Song);
	const int BPM = player.GetTempo();
	player.Play();
#endif

	TickLoader(width, height);
	// end loading process

	float deltaSeconds, prevSeconds = 0.0f;
	MSG msg;
	do
	{
		while (PeekMessage(&msg, NULL, 0, 0, PM_REMOVE))
		{
			if (msg.message == WM_QUIT)
			{
				break;
			}
			TranslateMessage(&msg);
			DispatchMessage(&msg);
		}

#ifdef NO_AUDIO
		float seconds = (GetTickCount() - start) * 0.001f;
		seconds *= SPEED;
		seconds += START_BEAT / BPM * 60.0f;
#endif

#ifdef AUDIO_64KLANG2
		float seconds = _64klang2_GetPlaybackTime();
#endif

#ifdef AUDIO_BASS
		unsigned __int64 pos = BASS_ChannelGetPosition(chan, BASS_POS_BYTE);
		float seconds = (float)BASS_ChannelBytes2Seconds(chan, pos);
#endif

#ifdef AUDIO_WAVESABRE
		float seconds = (float)player.GetSongPos();
#endif

		deltaSeconds = seconds - prevSeconds;
		prevSeconds = seconds;
		if (!evalDemo(seconds, seconds * ((float)BPM / 60.0f), width, height, deltaSeconds))
		{
			break;
		}
		SwapBuffers(device);
	} while (!GetAsyncKeyState(VK_ESCAPE));

	ExitProcess(0);
}
