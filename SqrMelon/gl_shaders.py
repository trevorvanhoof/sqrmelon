from OpenGL.GL import *
from OpenGL.GL.shaders import ShaderProgram


def compileProgram(*shaders, **named):
    """Create a new program, attach shaders and validate
    shaders -- arbitrary number of shaders to attach to the
        generated program.
    separable (keyword only) -- set the separable flag to allow 
        for partial installation of shader into the pipeline (see 
        glUseProgramStages)
    retrievable (keyword only) -- set the retrievable flag to 
        allow retrieval of the program binary representation, (see 
        glProgramBinary, glGetProgramBinary)
    validate (keyword only) -- if False, suppress automatic 
        validation against current GL state. In advanced usage 
        the validation can produce spurious errors. Note: this 
        function is *not* really intended for advanced usage,
        if you're finding yourself specifying this flag you 
        likely should be using your own shader management code.
    This convenience function is *not* standard OpenGL,
    but it does wind up being fairly useful for demos
    and the like.  You may wish to copy it to your code
    base to guard against PyOpenGL changes.
    Usage:
        shader = compileProgram(
            compileShader( source, GL_VERTEX_SHADER ),
            compileShader( source2, GL_FRAGMENT_SHADER ),
        )
        glUseProgram( shader )
    Note:
        If (and only if) validation of the linked program
        *passes* then the passed-in shader objects will be
        deleted from the GL.
    returns ShaderProgram() (GLuint) program reference
    raises RuntimeError when a link/validation failure occurs
    """
    program = glCreateProgram()
    if named.get('separable'):
        glProgramParameteri( program, separate_shader_objects.GL_PROGRAM_SEPARABLE, GL_TRUE )
    if named.get('retrievable'):
        glProgramParameteri( program, get_program_binary.GL_PROGRAM_BINARY_RETRIEVABLE_HINT, GL_TRUE )
    for shader in shaders:
        glAttachShader(program, shader)
    program = ShaderProgram( program )
    glLinkProgram(program)
    if named.get('validate', True):
        program.check_validate()
    program.check_linked()
    for shader in shaders:
        glDeleteShader(shader)
    return program
