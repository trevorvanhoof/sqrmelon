#pragma once



#include <Windows.h>
#include <gl/GL.h>



#define GL_FRAGMENT_SHADER 0x8B30
#define GL_VERTEX_SHADER 0x8B31
#define GL_COMPILE_STATUS 0x8B81
#define GL_LINK_STATUS 0x8B82
#define GL_INFO_LOG_LENGTH 0x8B84
#define GL_RGBA32F 0x8814
#define GL_COLOR_ATTACHMENT0 0x8CE0
#define GL_FRAMEBUFFER 0x8D40
#define GL_TEXTURE0 0x84C0
#define GL_TEXTURE1 0x84C1
#define GL_TEXTURE_3D 0x806F
#define GL_TEXTURE_WRAP_R 0x8072



typedef void(__stdcall*glUseProgram_proc)(GLuint);
typedef GLint(__stdcall*glGetUniformLocation_proc)(GLuint, const char*);
typedef void(__stdcall*glUniform1f_proc)(GLint, float);
typedef void(__stdcall*glUniform2f_proc)(GLint, float, float);
typedef void(__stdcall*glUniform3f_proc)(GLint, float, float, float);
typedef void(__stdcall*glUniform4f_proc)(GLint, float, float, float, float);
typedef void(__stdcall*glUniform1fv_proc)(GLint, GLsizei, const float*);
typedef void(__stdcall*glUniform2fv_proc)(GLint, GLsizei, const float*);
typedef void(__stdcall*glUniform3fv_proc)(GLint, GLsizei, const float*);
typedef void(__stdcall*glUniform4fv_proc)(GLint, GLsizei, const float*);
typedef void(__stdcall*glUniformMatrix3fv_proc)(GLint, GLsizei, GLboolean, const GLfloat*);
typedef void(__stdcall*glUniformMatrix4fv_proc)(GLint, GLsizei, GLboolean, const GLfloat*);
typedef void(__stdcall*glGenFramebuffers_proc)(GLsizei, GLuint*);
typedef void(__stdcall*glFramebufferTexture2D_proc)(GLenum, GLenum, GLenum, GLuint, GLint);
typedef void(__stdcall*glBindFramebuffer_proc)(GLenum, GLuint);
typedef void(__stdcall*glDrawBuffers_proc)(GLsizei, const GLenum*);
typedef void(__stdcall*glActiveTexture_proc)(GLenum);
typedef void(__stdcall*glUniform1i_proc)(GLint, GLint);
typedef void(__stdcall*glTexImage3D_proc)(GLenum, GLint, GLint, GLsizei, GLsizei, GLsizei, GLint, GLenum, GLenum, const void*);



#define glUseProgram ((glUseProgram_proc)wglGetProcAddress("glUseProgram"))
#define glGetUniformLocation ((glGetUniformLocation_proc)wglGetProcAddress("glGetUniformLocation"))
#define glUniform1f ((glUniform1f_proc)wglGetProcAddress("glUniform1f"))
#define glUniform2f ((glUniform2f_proc)wglGetProcAddress("glUniform2f"))
#define glUniform3f ((glUniform3f_proc)wglGetProcAddress("glUniform3f"))
#define glUniform4f ((glUniform4f_proc)wglGetProcAddress("glUniform4f"))
#define glUniform1fv ((glUniform1fv_proc)wglGetProcAddress("glUniform1fv"))
#define glUniform2fv ((glUniform2fv_proc)wglGetProcAddress("glUniform2fv"))
#define glUniform3fv ((glUniform3fv_proc)wglGetProcAddress("glUniform3fv"))
#define glUniform4fv ((glUniform4fv_proc)wglGetProcAddress("glUniform4fv"))
#define glUniformMatrix3fv ((glUniformMatrix3fv_proc)wglGetProcAddress("glUniformMatrix3fv"))
#define glUniformMatrix4fv ((glUniformMatrix4fv_proc)wglGetProcAddress("glUniformMatrix4fv"))
#define glGenFramebuffers ((glGenFramebuffers_proc)wglGetProcAddress("glGenFramebuffers"))
#define glFramebufferTexture2D ((glFramebufferTexture2D_proc)wglGetProcAddress("glFramebufferTexture2D"))
#define glBindFramebuffer ((glBindFramebuffer_proc)wglGetProcAddress("glBindFramebuffer"))
#define glDrawBuffers ((glDrawBuffers_proc)wglGetProcAddress("glDrawBuffers"))
#define glActiveTexture ((glActiveTexture_proc)wglGetProcAddress("glActiveTexture"))
#define glUniform1i ((glUniform1i_proc)wglGetProcAddress("glUniform1i"))
#define glTexImage3D ((glTexImage3D_proc)wglGetProcAddress("glTexImage3D"))


#if defined(_DEBUG)
typedef GLuint (WINAPI* PFNglCreateShader)(GLenum);
typedef void (WINAPI* PFNglShaderSource)(GLuint, GLsizei, const char**, void*);
typedef void (WINAPI* PFNglCompileShader)(GLuint);
typedef GLuint (WINAPI* PFNglCreateProgram)();
typedef void (WINAPI* PFNglAttachShader)(GLuint, GLuint);
typedef void (WINAPI* PFNglLinkProgram)(GLuint);
typedef void (WINAPI* PFNglDetachShader)(GLuint, GLuint);
typedef void (WINAPI* PFNglDeleteShader)(GLuint);
typedef void (WINAPI* PFNglGetShaderiv)(GLuint, GLenum, GLint*);
typedef void (WINAPI* PFNglGetShaderInfoLog)(GLuint, GLsizei, GLsizei*, char*);
typedef void (WINAPI* glGetProgramiv_proc)(GLuint, GLenum, GLint*);
typedef void (WINAPI* glGetProgramInfoLog_proc)(GLuint, GLsizei, GLsizei*, char*);

typedef void (WINAPI* glDeleteTextures_proc)(GLsizei, GLuint*);
typedef void (WINAPI* glDeleteFramebuffers_proc)(GLsizei, GLuint*);

#define glCreateShader ((PFNglCreateShader)wglGetProcAddress("glCreateShader"))
#define glShaderSource ((PFNglShaderSource)wglGetProcAddress("glShaderSource"))
#define glCompileShader ((PFNglCompileShader)wglGetProcAddress("glCompileShader"))
#define glCreateProgram ((PFNglCreateProgram)wglGetProcAddress("glCreateProgram"))
#define glProgramParameteri ((PFNglProgramParameteri)wglGetProcAddress("glProgramParameteri"))
#define glAttachShader ((PFNglAttachShader)wglGetProcAddress("glAttachShader"))
#define glLinkProgram ((PFNglLinkProgram)wglGetProcAddress("glLinkProgram"))
#define glDetachShader ((PFNglDetachShader)wglGetProcAddress("glDetachShader"))
#define glDeleteShader ((PFNglDeleteShader)wglGetProcAddress("glDeleteShader"))
#define glGetShaderiv ((PFNglGetShaderiv)wglGetProcAddress("glGetShaderiv"))
#define glGetShaderInfoLog ((PFNglGetShaderInfoLog)wglGetProcAddress("glGetShaderInfoLog"))
#define glGetProgramiv ((glGetProgramiv_proc)wglGetProcAddress("glGetProgramiv"))
#define glGetProgramInfoLog ((glGetProgramInfoLog_proc)wglGetProcAddress("glGetProgramInfoLog"))

#define glDeleteTextures ((glDeleteTextures_proc)wglGetProcAddress("glDeleteTextures"))
#define glDeleteFramebuffers ((glDeleteFramebuffers_proc)wglGetProcAddress("glDeleteFramebuffers"))

GLuint __stdcall glCreateShaderProgramv(GLenum type, GLsizei count, const char** strings);
#else
typedef GLuint(__stdcall*glCreateShaderProgramv_proc)(GLenum type, GLsizei count, const char** strings);
#define glCreateShaderProgramv ((glCreateShaderProgramv_proc)wglGetProcAddress("glCreateShaderProgramv"))
#endif
