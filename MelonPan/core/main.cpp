#include "../content/config.h"

#ifdef EIDOLON
#include "../content/Eidolon/generated.hpp"
#undef NO_AUDIO
#define AUDIO_64KLANG2
#undef AUDIO_WAVESABRE
#undef AUDIO_BASS
#undef 
#elif defined(BROS_BEFORE_FOES)
#include "../content/BrosBeforeFoes/generated.hpp"
#undef NO_AUDIO
#undef AUDIO_64KLANG2
#define AUDIO_WAVESABRE
#undef AUDIO_BASS
#else
#include "../content/generated.hpp"
#endif

#ifdef SUPPORT_PNG
#define STB_IMAGE_IMPLEMENTATION
#include "../extensions/stb_image.h"
#endif

#ifdef assert
#undef assert
#endif

#ifdef _DEBUG
#define assert(expr) if(!(expr)) __debugbreak();
#else
#define assert(expr) if(!(expr)) {}
#endif

#ifdef EXPORT_FRAMES_FPS
#define __STDC_LIB_EXT1__
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "../extensions/stb_image_write.h"
#undef NO_AUDIO
#undef AUDIO_64KLANG2
#undef AUDIO_WAVESABRE
#undef AUDIO_BASS
#endif

#define VC_EXTRALEAN
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <GL/gl.h>
#include <xmmintrin.h>

#ifdef _DEBUG
#include <cmath>
#include <fstream>
#include <sstream>
#include <string>
#else
#ifdef AUDIO_WAVESABRE
#undef _CRT_FUNCTIONS_REQUIRED
extern "C" const IID GUID_NULL = { 0, 0, 0, {0,0,0,0} };
extern "C" {
    int _purecall() { return 0; };
    int _fltused; 
    extern float sinf(float);
    extern float sqrtf(float);
    extern float atan2f(float,float);
    extern float acosf(float);

    _Check_return_ __inline float __CRTDECL cosf(_In_ float _X) { return sinf(_X + 3.14159265359f * 0.5f); }
    _Check_return_ __inline float __CRTDECL tanf(_In_ float _X) { return sinf(_X) / cosf(_X); }
}
void* __cdecl operator new(size_t size) { return HeapAlloc(GetProcessHeap(), 0, size); }
void __cdecl operator delete(void* ptr) { HeapFree(GetProcessHeap(), 0, ptr); }
#else
extern "C" {
    int _purecall() { return 0; };
    int _fltused; 
    extern float sinf(float);
    extern float sqrtf(float);
    extern float atan2f(float,float);
    extern float acosf(float);
}
inline float cosf(float v) { return sinf(v + 3.14159265359f * 0.5f); }
inline float tanf(float v) { return sinf(v) / cosf(v); }
#endif
#endif

#include "wglext.h"
#include "wglext.inl"

#ifdef NO_AUDIO
#include "../synths/noaudio.hpp"
#endif
#ifdef AUDIO_64KLANG2
#include "../synths/64klang2.hpp"
#endif
#ifdef AUDIO_BASS
#include "../synths/bass.hpp"
#endif
#ifdef AUDIO_WAVESABRE
#include "../synths/wavesabre.hpp"
#endif

#ifdef RESOLUTION_SELECTOR
#include "../extensions/Dialog.h"

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

// http://sizecoding.blogspot.com/2007/10/tiny-opengl-windowing-code.html
constexpr const PIXELFORMATDESCRIPTOR pfd = {
    sizeof(PIXELFORMATDESCRIPTOR), 1, PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER, 32, 0, 0, 0, 0, 0, 0, 
    0, 0, 0, 0, 0, 0, 0, 32, 0, 0, 0, 0, 0, 0, 0 
};

constexpr const GLenum outputBuffers[]{ GL_COLOR_ATTACHMENT0, GL_COLOR_ATTACHMENT0 + 1, GL_COLOR_ATTACHMENT0 + 2, GL_COLOR_ATTACHMENT0 + 3, GL_COLOR_ATTACHMENT0 + 4, GL_COLOR_ATTACHMENT0 + 5 };

struct Program {
    unsigned char stitchCount;

    inline const char* stitch(unsigned char index) const { 
        unsigned int* stitchIndices = (unsigned int*)(&stitchCount + 1);
        assert(index < stitchCount);
        return (const char*)(data + stitchIndices[index]); 
    }
};

struct Programs {
    inline const Program& get(unsigned short index) const {
        unsigned int* programIndices = (unsigned int*)(data + programsIndex);
        assert(index < programCount);
        return *(const Program*)(data + programIndices[index]);
    }
};

struct FramebufferInfo {
    unsigned short width;
    unsigned short height;
    unsigned char factor;
    unsigned char realtime_is3d_numOutputBuffers;
    inline const bool realtime() const { return realtime_is3d_numOutputBuffers & (1 << 7); }
    inline const bool is3d() const { return realtime_is3d_numOutputBuffers & (1 << 6); }
    inline const bool tile() const { return realtime_is3d_numOutputBuffers & (1 << 5); }
    inline const unsigned char numOutputBuffers() const { return realtime_is3d_numOutputBuffers & 0b00011111; }
};

struct Key {
    float inTangentY;
    float x;
    float y;
    float outTangentY;
};

constexpr const float inf = __builtin_huge_valf(); // TODO: This does not seem to match what we have in our data

struct Curve {
    unsigned short keyCount;
    inline float evaluate(float localBeat) const {
        // A float array starts after keyCount, but virtually a key starts with an inTangent that we didn't save
        // so we just shift the address by - 1 instead to make space of a float32 that we never actually read.
        const Key* keys = (const Key*)(&keyCount - 1);
        // TODO: Use faster key scan algorithm?
        for(unsigned short i = 0; i < keyCount; ++i) {
            const Key& rhs = keys[i];
            if(rhs.x > localBeat) {
                if (i == 0)
                    return rhs.y;
                const Key& lhs = keys[i - 1];
                // stepped tangent hack
                if (lhs.outTangentY == inf) 
                    return lhs.y;
                // cubic hermite spline sample
                float p1 = lhs.outTangentY;
                float p2 = rhs.inTangentY;
                float dx = rhs.x - lhs.x;
                float dy = rhs.y - lhs.y;
                float c0 = (p1 + p2 - dy - dy);
                float c1 = (dy + dy + dy - p1 - p1 - p2);
                float c2 = p1;
                float c3 = lhs.y;
                float t = (localBeat - lhs.x) / dx;
                return t * (t * (t * c0 + c1) + c2) + c3;
            }
        }
        return keys[keyCount - 1].y;
    }
};

struct ShotUniforms {
    unsigned short sizeOf;
    unsigned char uniformCount;
    // unsigned int uniformNameOffsets[uniformCount];
    // unsigned char uniformSizes[uniformCount];
    // unsigned int curveOffsets[sum(uniformSizes)];

    inline const char* uniformName(unsigned char index) const {
        unsigned int* uniformNameIndices = (unsigned int*)(&uniformCount + 1);
        return (const char*)(data + uniformNameIndices[index]);
    }

    inline const unsigned char uniformSize(unsigned char index) const {
        unsigned char* uniformSizes = (unsigned char*)(&uniformCount + 1 + uniformCount * 4);
        return uniformSizes[index];
    }

    inline const Curve& curve(unsigned int index) const {
        unsigned int* curveOffsets = (unsigned int*)(&uniformCount + 1 + uniformCount * 5);
        return *(const Curve*)(data + curveOffsets[index]);
    }
};

struct ScenePass {
    unsigned short programId; // index into the program handles array
    unsigned char fboId; // index into the frame buffer handles array
    unsigned char cboCount;

    inline unsigned char cbo(unsigned char index) const { // index into the color buffer handles array
        assert(index < cboCount);
        unsigned char* cboIds = (unsigned char*)(&cboCount + 1);
        unsigned char cbo = cboIds[index];
        return cbo;
    }
};

struct ScenePasses {
    unsigned char passCount;

    inline const ScenePass& get(unsigned char index) const {
        assert(index < passCount);
        unsigned int* passIndices = (unsigned int*)(&passCount + 1);
        return *(const ScenePass*)(data + passIndices[index]);
    }
};

#ifdef EIDOLON
#include "../content/Eidolon/animationprocessor.inl"
#else
#include "../content/animationprocessor.inl"
#endif

HDC device;

#ifndef NO_LOADER
float loaderStep = 0;
float loaderSteps = 0;
GLint loaderUniform;
GLuint loaderProgram;

const char* loaderCode = "#version 410\nuniform vec2 r;uniform float t;out vec3 c;void main(){"
#ifdef SMALLER_LOADER
"c=vec3(step(gl_FragCoord.x/r.x,t));"
#else
"vec2 a=(gl_FragCoord.xy*2-r)/r.y,"
"b=abs(a)-vec2(r.x/r.y-.25,.15),"
"d=a;"
"a*=4;"
"float e=max(b.x,b.y),"
"f=floor(a.x),"
"g=sin(f*10)*10;"
"a.x=fract(a.x)-.5;"
"a.y+=floor(g)*.04;"
"d.x*=22;"
"d.x+=1.5;"
"c=vec3(1,.25,.2)*step(e,0)*step(gl_FragCoord.x/r.x,t)*step(.1*fract(g)+.05,length(a))"
"+mix(vec3(.25,.4,.15),vec3(.4,.6,.2),step(sin(d.x+sin(d.y*100+d.x*.5)*.15),.5))*step(abs(e-.08)-.03,0);"
#endif
"}";

void initLoader(int steps, int screenWidth, int screenHeight) {
    loaderSteps = (float)steps;
    loaderProgram = glCreateShaderProgramv(GL_FRAGMENT_SHADER, 1, &loaderCode);
    glUseProgram(loaderProgram);
    float r[2];
    r[0] = (float)screenWidth;
    r[1] = (float)screenHeight;
    glUniform2fv(glGetUniformLocation(loaderProgram, "r"), 1, r);
    loaderUniform = glGetUniformLocation(loaderProgram, "t");
}

void tickLoader() {
    glBindFramebuffer(GL_FRAMEBUFFER, 0);
    loaderStep += 1.0f;
    glUseProgram(loaderProgram);
    glUniform1f(loaderUniform, loaderStep / loaderSteps);
    glRecti(-1, -1, 1, 1);
    SwapBuffers(device);
}
#else
__forceinline void initLoader(int steps, int screenWidth, int screenHeight) {}
__forceinline void tickLoader() {}
#endif

#ifdef SUPPORT_PNG
GLuint imageTextures[textureCount];

void loadTextures() {
    glGenTextures(textureCount, imageTextures);
    for(unsigned int i = 0; i < textureCount; ++i) {
        glBindTexture(GL_TEXTURE_2D, imageTextures[i]);
        int x, y, n;
        unsigned char* data = stbi_load(texturePaths[i * 2 + 1], &x, &y, &n, 0);
        assert(data != nullptr);
        GLenum format[4] = { GL_RED, GL_RG, GL_RGB, GL_RGBA };
        --n;
        assert(n >= 0 && n < 4);
        glTexImage2D(GL_TEXTURE_2D, 0, format[n], x, y, 0, format[n], GL_UNSIGNED_BYTE, data);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        // sqrMelon leaves wrapping on default
        stbi_image_free(data);
        tickLoader();
    }
}

void setTextureUniforms(GLuint program, GLenum nextActiveTexture) {
    for(unsigned int i = 0; i < textureCount; ++i) {
        glActiveTexture(GL_TEXTURE0 + nextActiveTexture + i);
        glBindTexture(GL_TEXTURE_2D, imageTextures[i]);
        glUniform1i(glGetUniformLocation(program, texturePaths[i * 2]), GL_TEXTURE0 + nextActiveTexture + i);
    }
}
#endif

#ifdef _DEBUG
int WINAPI WinMain( HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow ) {
#else
int main() {
#endif
    // Data
    // This is an array of floats, we can index into this pointer.
    const float* const shotEndTimes = (const float*)(data + shotEndTimesIndex);
    // Index to the start of the pass list used by each shot.
    const unsigned int* const shotSceneIds = (const unsigned int*)(data + shotSceneIdsIndex);
    // This is an array of framebuffers, we can index into this pointer.
    const FramebufferInfo* const framebuffers = (const FramebufferInfo*)(data + framebuffersInfoIndex);

    // Cache
    // Each curve will write what glUniform#f() call to use.
    unsigned char animationTypeBuffer[maxAnimations];
    // Each curve will write its evaluated values in a block of 4 floats, some may be unused.
    float animationBuffer[4 * maxAnimations];
    // Uniform names
    char uImages2D[] = "uImages[   ";
    char uImages3D[] = "uImages3D[   ";

    // State
    unsigned int currentShotIndex = 0;
    // This is an array of shots, but they are not of a fixed size, so we can not index into the pointer.
    const ShotUniforms* currentShot = (const ShotUniforms*)(data + shotAnimationInfoIndex);
    // This is an array of scenes, but they are not of a fixed size, so we can not index into the pointer.
    const ScenePasses* currentScene = (const ScenePasses*)(data + shotSceneIds[currentShotIndex]);

    int screenWidth, screenHeight;
    bool isWindowed;
    HWND window;

#ifdef RESOLUTION_SELECTOR
    // resolution selector
    INT_PTR result = DialogBoxA(GetModuleHandleA(NULL), MAKEINTRESOURCEA(IDD_DIALOGCONFIG), NULL, ConfigDialogProc);
    if (result != IDOK)
        return;
    switch (resolutionIndex) {
    case 1: // HD ready
        screenWidth = 1280;
        screenHeight = 720;
        break;
    case 2: // full HD
        screenWidth = 1920;
        screenHeight = 1080;
        break;
    default: // native
        screenWidth = GetSystemMetrics(SM_CXSCREEN);
        screenHeight = GetSystemMetrics(SM_CYSCREEN);
        isWindowed = true; // going to full screen only makes sense if we want to change the resolution of the screen
        break;
    }
#else
    screenWidth = DEMO_WIDTH;
    screenHeight = DEMO_HEIGHT;

    #if defined(IS_WINDOWED) || DEMO_WIDTH == 0 || DEMO_HEIGHT == 0
    isWindowed = true;
    #endif

#endif
    if (isWindowed) {
        // https://www.pouet.net/topic.php?which=9894&page=1
        window = CreateWindowExA(0, (LPCSTR)49177, WINDOW_TITLE, WS_POPUP | WS_VISIBLE, 0, 0, screenWidth, screenHeight, 0, 0, 0, 0);
    } else {
        DEVMODEA dmScreenSettings {
            "", 0, 0, sizeof(dmScreenSettings), 0, DM_PELSWIDTH | DM_PELSHEIGHT | DM_DISPLAYFIXEDOUTPUT,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, "", 0, 0, (DWORD)screenWidth, (DWORD)screenHeight, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
        };
        ChangeDisplaySettingsA(&dmScreenSettings, CDS_FULLSCREEN);
        window = CreateWindowExA(0, (LPCSTR)49177, WINDOW_TITLE, WS_POPUP | WS_VISIBLE | WS_MAXIMIZE, 0, 0, 0, 0, 0, 0, 0, 0);
    }

    ShowCursor(0);

    device = GetDC(window);
    SetPixelFormat(device, ChoosePixelFormat(device, &pfd), &pfd);
    wglMakeCurrent(device, wglCreateContext(device));

    #if DEMO_WIDTH == 0 || DEMO_HEIGHT == 0
    RECT area;
    GetClientRect(window, &area);
    screenWidth = area.right - area.left;
    screenHeight = area.bottom - area.top;
    #endif

    initLoader( 1 /*initial tick*/ + programCount + framebuffersCount + 1 /*audio*/ + staticFramebuffersCount
#ifdef SUPPORT_PNG
        + textureCount
#endif
        , screenWidth, screenHeight);
    tickLoader();

#ifdef SUPPORT_PNG
    // Import images
    loadTextures();
#endif

    // Compile shaders
    GLuint programHandles[programCount];
    {
        const char* stitchBuffer[255];
        const Programs& programs = *(const Programs*)(data + programsIndex);
        for(unsigned short i = 0; i < programCount; ++i) {
            const Program& program = programs.get(i);
            for(unsigned char j = 0; j < program.stitchCount; ++j) {
                stitchBuffer[j] = program.stitch(j);
            }
            programHandles[i] = glCreateShaderProgramv(GL_FRAGMENT_SHADER, program.stitchCount, stitchBuffer);

#ifdef USE_OUTPUT_DEBUG_STRING
            // DEBUG: Output the shader files; named after the order in the handles array.
            std::stringstream name;
            name << "program_" << (int)i << ".glsl";
            std::ofstream ofs(name.str());
            for(unsigned char j = 0; j < program.stitchCount; ++j) {
                ofs << stitchBuffer[j];
            }
#endif
            tickLoader();
        }
    }

    // Set up buffers
    GLuint fboHandles[framebuffersCount];
    int fboCboStartIndex[framebuffersCount];
    GLuint cboHandles[cboCount];
    bool cboIs3D[cboCount];
    {
        glGenFramebuffers(framebuffersCount, fboHandles);
        glGenTextures(cboCount, cboHandles);

        GLuint* nextCbo = cboHandles;
        bool* next3D = cboIs3D;

#ifdef USE_OUTPUT_DEBUG_STRING
        {
            std::stringstream info;
            info << "current shot index: " << currentShotIndex << " | using scene: " << shotSceneIds[currentShotIndex] << std::endl;
            std::string tmp = info.str();
            OutputDebugStringA(tmp.c_str());
        }
#endif

        for(unsigned char i = 0; i < framebuffersCount; ++i) {
            const FramebufferInfo& framebuffer = framebuffers[i];
            glBindFramebuffer(GL_FRAMEBUFFER, fboHandles[i]);
            fboCboStartIndex[i] = (int)(nextCbo - cboHandles);

#ifdef USE_OUTPUT_DEBUG_STRING
            // DEBUG: Output the framebuffer info to the debugger.
            std::stringstream info;
            info << "fbo index: " << (int)i << " | output count: " << (int)framebuffer.numOutputBuffers() << " | first cbo index: " << (size_t)(nextCbo - cboHandles) << std::endl;
            std::string tmp = info.str();
            OutputDebugStringA(tmp.c_str());
#endif

            for(unsigned char j = 0; j < framebuffer.numOutputBuffers(); ++j) {
                assert(framebuffer.numOutputBuffers() < sizeof(outputBuffers) / sizeof(GLenum));
                glBindTexture(GL_TEXTURE_2D, *nextCbo);
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA32F, 
                    framebuffer.width ? framebuffer.width : screenWidth / framebuffer.factor,
                    framebuffer.height ? framebuffer.height : screenHeight / framebuffer.factor,
                    0, GL_RGBA, GL_FLOAT, nullptr);
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
                if(!framebuffer.tile()) {
                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP);
                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP);
                }
                glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0 + j, GL_TEXTURE_2D, *nextCbo, 0);
                ++nextCbo;

                *next3D = framebuffer.is3d();
                ++next3D;
            }

            tickLoader();
        }
    }

    bool first = true;
    float prevSeconds = 0.0f;
    float deltaSeconds = 0.0f;
    
    animationprocessor_init();
#ifndef EXPORT_FRAMES_FPS
    audioInit();
#endif
    tickLoader();

#ifdef EXPORT_FRAMES_FPS 
    void* exportFrameBuffer = HeapAlloc(GetProcessHeap(), 0, screenWidth * screenHeight * 3);
    unsigned int exportFrame = 0;
    constexpr const float deltaSeconds = (float)(1.0 / EXPORT_FRAMES_FPS);
#endif

#ifdef ENABLE_WINDOWS_EVENTS
    MSG msg;
#endif

    float beats = 0.0f;
    do {
#ifdef EXPORT_FRAMES_FPS
        float seconds = (float)((double)exportFrame / (double)EXPORT_FRAMES_FPS);
#else
        float seconds = audioCursor();
        deltaSeconds = seconds - prevSeconds;
#endif
        seconds = (seconds + DEBUG_START_SECONDS) * DEBUG_SPEED_FACTOR;
        deltaSeconds *= DEBUG_SPEED_FACTOR;

        beats = seconds * beatsPerSecond;

        // Evaluate the animation
        float localBeats = beats - ((currentShotIndex == 0) ? 0.0f : shotEndTimes[currentShotIndex - 1]);
        unsigned int curveIndex = 0;
        for(unsigned char i = 0; i < currentShot->uniformCount; ++i) {
            unsigned char size = currentShot->uniformSize(i);
            animationTypeBuffer[i] = size;
            for(int element = 0; element < size; ++element) {
                const Curve& curve = currentShot->curve(curveIndex);
                float value = curve.evaluate(localBeats);
                animationBuffer[4 * i + element] = value;
                animationprocessor__doCallback();
                ++curveIndex;
            }
        }

        // Render the passes
        for(unsigned char i = 0; i < currentScene->passCount; ++i) {
            const ScenePass& pass = currentScene->get(i);

            GLsizei w = screenWidth;
            GLsizei h = screenHeight;
            if (pass.fboId == 0b11111111) {
                if (first) continue;
                glBindFramebuffer(GL_FRAMEBUFFER, 0);
            } else {
                const FramebufferInfo& framebuffer = framebuffers[pass.fboId];
                if (first == framebuffer.realtime()) continue;
                glBindFramebuffer(GL_FRAMEBUFFER, fboHandles[pass.fboId]);
                glDrawBuffers(framebuffer.numOutputBuffers(), outputBuffers);
                w = framebuffer.width ? framebuffer.width : w / framebuffer.factor;
                h = framebuffer.height ? framebuffer.height : h / framebuffer.factor;
            }
            glViewport(0, 0, w, h);

            GLuint program = programHandles[pass.programId];
            glUseProgram(program);

#ifdef USE_OUTPUT_DEBUG_STRING
            // DEBUG: Output the pass info to the debugger.
            std::stringstream info;
            info << "pass index: " << (int)i << " | width: " << (int)w << " | height: " << (int)h << " | program index: " << (int)pass.programId << " | cbos: " << (int)pass.cboCount << std::endl;
#endif

            // Bind inputs
            unsigned char j2d = 0;
            unsigned char j3d = 0;
            for(unsigned char j = 0; j < pass.cboCount; ++j) {
                glActiveTexture(GL_TEXTURE0 + j);
                GLuint cbo = cboHandles[pass.cbo(j)];

#if 0
                // DEBUG: OUTPUT A DIFFERENT COLOR BUFFER WHEN DRAWING TO SCREEN
                if (pass.fboId == 0b11111111)
                    cbo = cboHandles[0];
#endif

                bool is3d = cboIs3D[pass.cbo(j)];
#ifdef USE_OUTPUT_DEBUG_STRING
                info << "\t" << (int)pass.cbo(j) << ", is3d: " << is3d << std::endl;
#endif
                const bool isTwoDigits = j > 9;
                char* dest = is3d ? uImages3D + 10 : uImages2D + 8;
                *dest++ = isTwoDigits ? '0' + j / 10 : '0' + j % 10;
                *dest++ = isTwoDigits ? '0' + j % 10 : ']';
                *dest++ = isTwoDigits ? ']' : 0;
                glBindTexture(is3d ? GL_TEXTURE_3D : GL_TEXTURE_2D, cbo);
                glUniform1i(glGetUniformLocation(program, is3d ? uImages3D : uImages2D), j);
            }

#ifdef USE_OUTPUT_DEBUG_STRING
            {
                std::string tmp = info.str();
                OutputDebugStringA(tmp.c_str());
            }
#endif

            // Forward uniforms
            for(unsigned char i = 0; i < currentShot->uniformCount; ++i) {

#ifdef USE_OUTPUT_DEBUG_STRING
                std::stringstream uniformInfo;
                uniformInfo << "Setting uniform: " << currentShot->uniformName(i) << " | vec" << (int)animationTypeBuffer[i] << ": ";
                switch(animationTypeBuffer[i]) {
                case 1:
                    uniformInfo << animationBuffer[4 * i];
                    break;
                case 2:
                    uniformInfo << animationBuffer[4 * i] << ", ";
                    uniformInfo << animationBuffer[4 * i + 1];
                    break;
                case 3:
                    uniformInfo << animationBuffer[4 * i] << ", ";
                    uniformInfo << animationBuffer[4 * i + 1] << ", ";
                    uniformInfo << animationBuffer[4 * i + 2];
                    break;
                case 4:
                    uniformInfo << animationBuffer[4 * i] << ", ";
                    uniformInfo << animationBuffer[4 * i + 1] << ", ";
                    uniformInfo << animationBuffer[4 * i + 2] << ", ";
                    uniformInfo << animationBuffer[4 * i + 3];
                    break;
                }
                uniformInfo << std::endl;
                std::string tmp = uniformInfo.str();
                OutputDebugStringA(tmp.c_str());
#endif

                GLint loc = glGetUniformLocation(program, currentShot->uniformName(i));
                switch(animationTypeBuffer[i]) {
                case 1:
                    glUniform1fv(loc, 1, &animationBuffer[4 * i]);
                    break;
                case 2:
                    glUniform2fv(loc, 1, &animationBuffer[4 * i]);
                    break;
                case 3:
                    glUniform3fv(loc, 1, &animationBuffer[4 * i]);
                    break;
                case 4:
                    glUniform4fv(loc, 1, &animationBuffer[4 * i]);
                    break;
                }
            }

            // Global uniforms
            glUniform2f(glGetUniformLocation(program, "uResolution"), (float)w, (float)h);
            glUniform1f(glGetUniformLocation(program, "uSeconds"), seconds);
            glUniform1f(glGetUniformLocation(program, "uBeats"), beats);
#ifdef USE_OUTPUT_DEBUG_STRING
            {
                std::stringstream uniformInfo;
                uniformInfo << "Setting uniform: uResolution | vec2: " << (int)w << ", " << (int)h << std::endl;
                uniformInfo << "Setting uniform: uSeconds | vec1: " << seconds << std::endl;
                uniformInfo << "Setting uniform: uBeats | vec1: " << beats << std::endl;
                std::string tmp = uniformInfo.str();
                OutputDebugStringA(tmp.c_str());
            }
#endif

#ifdef SUPPORT_PNG
            // Global textures
            setTextureUniforms(program, pass.cboCount);
#endif

            // animationprocessor
            animationprocessor__doFinalize();

            glRecti(-1, -1, 1, 1);

            // If pass is 3D, convert 2D -> 3D here so that the next time we look up the texture in cboHandles it is GL_TEXTURE_3D!
            if(pass.fboId != 0b11111111) {
                const FramebufferInfo& framebuffer = framebuffers[pass.fboId];
                int w = framebuffer.width ? framebuffer.width : screenWidth / framebuffer.factor;
                int h = framebuffer.height ? framebuffer.height : screenHeight / framebuffer.factor;
                float* buffer = (float*)HeapAlloc(GetProcessHeap(), 0, w * h * 4 * sizeof(float));
                if(framebuffer.is3d()) {
                    for (int i = 0; i < framebuffer.numOutputBuffers(); ++i) {
                        GLuint& texture = cboHandles[fboCboStartIndex[i]];
                        
                        glBindTexture(GL_TEXTURE_2D, texture);
                        glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_FLOAT, buffer);
                        glBindFramebuffer(GL_FRAMEBUFFER, 0);

                        glGenTextures(1, &texture);
                        glBindTexture(GL_TEXTURE_3D, texture);
                        glTexImage3D(GL_TEXTURE_3D, 0, GL_RGBA32F, h, h, h, 0, GL_RGBA, GL_FLOAT, buffer);

                        glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
                        glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
                        if(!framebuffer.tile())
                        {
                            glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_S, GL_CLAMP);
                            glTexParameteri(GL_TEXTURE_3D, GL_TEXTURE_WRAP_T, GL_CLAMP);
                        }
                    }
                }
                HeapFree(GetProcessHeap(), 0, buffer);
            }

            if(first)
                tickLoader();
        }

        SwapBuffers(device);

        if (currentShotIndex < shotCount && beats >= shotEndTimes[currentShotIndex]) { 
            ++currentShotIndex;
            currentShot = (const ShotUniforms*)(((unsigned char*)currentShot) + currentShot->sizeOf);
            currentScene = (const ScenePasses*)&data[shotSceneIds[currentShotIndex]];
        }

        if (first) {
            // Make sure all static textures are baked before we actually start the demo
#ifndef EXPORT_FRAMES_FPS
            audioPlay();
#endif
            first = false;
            continue;
        } else {
            prevSeconds = seconds;
        }

#ifdef EXPORT_FRAMES_FPS 
        glPixelStorei(GL_PACK_ALIGNMENT, 1);
        glReadBuffer(GL_BACK_LEFT);
        glReadPixels(0, 0, screenWidth, screenHeight, GL_RGB, GL_UNSIGNED_BYTE, exportFrameBuffer);
        char buf[128];
        ZeroMemory(buf, 128);
        sprintf_s(buf, "frame%d.png", exportFrame++);
        stbi_write_png(buf, screenWidth, screenHeight, 3, exportFrameBuffer, screenWidth * 3);
#endif

#ifdef ENABLE_WINDOWS_EVENTS
        while (PeekMessage(&msg, NULL, 0, 0, PM_REMOVE)) {
            if (msg.message == WM_QUIT)
                break;
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        }
#endif
    } while (!GetAsyncKeyState(VK_ESCAPE) && beats < shotEndTimes[shotCount - 1]);

    ExitProcess(0);
}
