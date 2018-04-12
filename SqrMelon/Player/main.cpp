#include "settings.h"
#include "generated.hpp"
#include "64klang2/SynthPlayer.h"
#include "64klang2/SynthAllocator.h"
#include "64klang2/sample_t.h"

// #define SUPPORT_3D_TEXTURE

#ifndef DEMO_WIDTH
#define DEMO_WIDTH 1280
#endif
#ifndef DEMO_HEIGHT
#define DEMO_HEIGHT 720
#endif

// #define NO_AUDIO
#ifdef NO_AUDIO
	#define BPM 124.0f
	#define START_BEAT 0.0f
	#define SPEED 1.0f
#endif


extern "C"{int _fltused;}

const PIXELFORMATDESCRIPTOR pfd = { sizeof(PIXELFORMATDESCRIPTOR), 1, PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER, 32, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 32, 0, 0, 0, 0, 0, 0, 0 };

extern "C"
{
	extern float sinf(float);
	extern float sqrtf(float);
}
float cosf(float v) { return sinf(v + 3.14159265359f * 0.5f); }
float tanf(float v) { return sinf(v) / cosf(v); }

// Copied necessary functions from cgmath/Mat44.cpp::Mat44
// should probably just be included in project directly.
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

 bool evalDemo(float seconds, float beats, int width, int height, float deltaSeconds, bool isPrecalcStep=false)
{
	float localBeats;
	int shot = shotAtBeats(beats, localBeats);
	if(shot == -1)
		return false;
	int animOffset = gIntData[shot * 2 + gShotAnimationDataIds];
	int animEntries = gIntData[shot * 2 + gShotAnimationDataIds + 1];
	int scene = gIntData[shot + gShotScene];
	int passCursor = 0;

	// Evaluate curves & physics and store in buffer
	for(int uniformId = 0; uniformId < animEntries; ++uniformId)
	{
		int idx = animOffset + uniformId * 10;

		animData[uniformId * 4] = evalCurve(&gFloatData[gIntData[idx + gShotUniformData + 2]], gIntData[idx + gShotUniformData + 3], localBeats);
		if(gIntData[idx + gShotUniformData + 1] > 1)
			animData[uniformId * 4 + 1] = evalCurve(&gFloatData[gIntData[idx + gShotUniformData + 4]], gIntData[idx + gShotUniformData + 5], localBeats);
		if(gIntData[idx + gShotUniformData + 1] > 2)
			animData[uniformId * 4 + 2] = evalCurve(&gFloatData[gIntData[idx + gShotUniformData + 6]], gIntData[idx + gShotUniformData + 7], localBeats);
		if(gIntData[idx + gShotUniformData + 1] > 3)
			animData[uniformId * 4 + 3] = evalCurve(&gFloatData[gIntData[idx + gShotUniformData + 8]], gIntData[idx + gShotUniformData + 9], localBeats);
		
		// Do what python does in animationprocessor.py
		if(lstrcmpiA(gTextPool[gIntData[idx + gShotUniformData]], "uOrigin") == 0)
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
			uFrustum[0] = -xfov;uFrustum[1] = -tfov;uFrustum[2] = 1.0f;
			uFrustum[4] = xfov;uFrustum[5] = -tfov;uFrustum[6] = 1.0f;
			uFrustum[8] = -xfov;uFrustum[9] = tfov;uFrustum[10] = 1.0f;
			uFrustum[12] = xfov;uFrustum[13] = tfov;uFrustum[14] = 1.0f;
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
		for(int uniformId = 0; uniformId < animEntries; ++uniformId)
		{
			int idx = animOffset + uniformId * 10;
			GLint loc = glGetUniformLocation(gPrograms[gIntData[passIndex * 2 + gPassProgramsAndTargets]], gTextPool[gIntData[idx + gShotUniformData]]);
			applyUniform(gIntData[idx + gShotUniformData + 1], loc, &animData[uniformId * 4]);
		}
		glUniformMatrix4fv(glGetUniformLocation(gPrograms[gIntData[passIndex * 2 + gPassProgramsAndTargets]], "uV"), 1, GL_FALSE, uV);
		glUniformMatrix4fv(glGetUniformLocation(gPrograms[gIntData[passIndex * 2 + gPassProgramsAndTargets]], "uFrustum"), 1, GL_FALSE, uFrustum);
		glRecti(-1, -1, 1, 1);
		// patch 3D textures
#ifdef SUPPORT_3D_TEXTURE
		if(!isPrecalcStep) 
			continue;
		int frameBufferId = gIntData[passIndex * 2 + gPassProgramsAndTargets + 1] - 1;
		if(frameBufferId < 0) 
			continue;
		int w = width;
		int h = height;
		widthHeight(frameBufferId, width, height, w, h);
		int is3d = gIntData[frameBufferId * gFrameBufferBlockSize + gFrameBufferData + 5];
		if(!is3d)
			continue;
		int j = 0;
		do
		{
			GLuint texture = *(gFrameBufferColorBuffers[frameBufferId] + j);
					
			glBindTexture(GL_TEXTURE_2D, texture);
			static float buffer[128*128*128*4];
			glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_FLOAT, buffer);
			glBindFramebuffer(GL_FRAMEBUFFER, 0);
					
			glGenTextures(1, &texture);
			*(gFrameBufferColorBuffers[frameBufferId] + j) = texture;
			glBindTexture(GL_TEXTURE_3D, texture);
			glTexImage3D(GL_TEXTURE_3D, 0, GL_RGBA32F, h, h, h, 0, GL_RGBA, GL_FLOAT, buffer);
					
			glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
			glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
			if(gIntData[frameBufferId * gFrameBufferBlockSize + gFrameBufferData + 4] == 0)
			{
				glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_S, GL_CLAMP);
				glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_T, GL_CLAMP);
			}
		}
		while(++j < gIntData[frameBufferId * gFrameBufferBlockSize + gFrameBufferData]);
#endif
	}
	while(++passCursor < gIntData[scene + gScenePassIds]);

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
int width;
int height;

void InitLoader()
{
	loaderProgram = glCreateShaderProgramv(GL_FRAGMENT_SHADER, 1, &loader);
}

void DrawLoader(float fade)
{
	glBindFramebuffer(GL_FRAMEBUFFER, 0);
	glUseProgram(loaderProgram);
	glUniform4f(glGetUniformLocation(loaderProgram, "u"), loaderState, (float)width, (float)height, fade);
	glRecti(-1, -1, 1, 1);
	SwapBuffers(device);
}

void TickLoader()
{
	loaderState += loaderStep;
	DrawLoader(1.0f);
}

#ifdef DEMO
#if DEMO_WIDTH != 0
DEVMODE dmScreenSettings =
{
	"", 0, 0, sizeof(dmScreenSettings), 0, DM_PELSWIDTH | DM_PELSHEIGHT | DM_DISPLAYFIXEDOUTPUT,
	0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, "", 0, 0, DEMO_WIDTH, DEMO_HEIGHT, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
};
#endif
#endif

void main()
{
#ifndef NO_AUDIO
	_64klang2_Init();
#endif
	
	#ifdef DEMO
	#if DEMO_WIDTH != 0
		ChangeDisplaySettings(&dmScreenSettings, CDS_FULLSCREEN);
	#endif
		HWND window = CreateWindowExA(0, (LPCSTR)49177, 0, WS_POPUP | WS_VISIBLE | WS_MAXIMIZE, 0, 0, 0, 0, 0, 0, 0, 0);
	#else
		HWND window = CreateWindowExA(0, (LPCSTR)49177, 0, WS_POPUP | WS_VISIBLE, 0, 0, DEMO_WIDTH, DEMO_HEIGHT, 0, 0, 0, 0);
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
		DrawLoader(opacity);
		opacity = (GetTickCount() - start) * 0.004f;
	}
	while(opacity < 1.0f);

	TickLoader();

	// TODO: put in threaded function and show loading process
	// compile shaders
	initPrograms();
	// allocate frame buffers
	initFrameBuffers(width, height);
	TickLoader();
	// precalc textures
	evalDemo(0.0f, 0.0f, width, height, 0.0f, true);
	TickLoader();

#ifdef NO_AUDIO
	start = GetTickCount();
#else
	float BPM = _64klang2_GetBPM();
	_64klang2_Play();
#endif
	TickLoader();
	// end loading process
	
	float deltaSeconds, prevSeconds = 0.0f;
	
	MSG msg;
	int safeguard = 2;

	do
	{
		while(PeekMessage(&msg, NULL, 0, 0, PM_REMOVE))
		{
			if(msg.message == WM_QUIT)
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
#else
		float seconds = _64klang2_GetPlaybackTime();
#endif
		deltaSeconds = seconds - prevSeconds;
		prevSeconds = seconds;
		if(!evalDemo(seconds, seconds * ((float)BPM / 60.0f), width, height, deltaSeconds))
		{
			break;
		}
		SwapBuffers(device);
	}
	while(!GetAsyncKeyState(VK_ESCAPE));

	ExitProcess(0);
}
