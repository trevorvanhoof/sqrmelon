#include "settings.h"



#if defined(_DEBUG)
GLuint __stdcall glCreateShaderProgramv(GLenum type, GLsizei count, const char** strings)
{
	const GLuint shader = glCreateShader(type);
	if (!shader)
		return 0;
	
	const GLuint program = glCreateProgram();
	if (!program)
		return 0;

	glShaderSource(shader, count, strings, NULL);
	glCompileShader(shader);
	
	GLint compiled = GL_FALSE;
	glGetShaderiv(shader, 0x8B81, &compiled);
	if (compiled)
	{
		glAttachShader(program, shader);
		glLinkProgram(program);
		glDetachShader(program, shader);
		
		glGetProgramiv(shader, 0x8B81, &compiled);
		if (!compiled)
		{
			char buffer[2048];
			GLsizei s;
			glGetProgramInfoLog(shader, 2048, &s, buffer);
			OutputDebugString(buffer);
			assert(false);
		}
	}
	else
	{
		char buffer[2048];
		GLsizei s;
		glGetShaderInfoLog(shader, 2048, &s, buffer);
		OutputDebugString(buffer);
		assert(false);
	}

	glDeleteShader(shader);
	return program;
}
#endif
