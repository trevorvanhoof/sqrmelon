"""error: resizing the window resuls in black content, even glClear does not hit it, glViewport seems correct
  so I think it is a texture resolution problem, am I talking to the wrong CBO?"""
from typing import Optional

from OpenGL.GL import *
from OpenGL.GL import shaders
from PySide6.QtOpenGL import QOpenGLWindow
from PySide6.QtWidgets import QApplication

from flex_project.rendering.programs import ProgramPool
from flex_project.utils import tt_json5
from flex_project.content.structure import BindFramebuffer, Clear, Command, DispatchCompute, DrawMesh, DrawRect, MeshAttribute, MeshAttributeType, Project, Template


def _sizeOfMeshAttributeType(value: MeshAttributeType) -> int:
    return {
        MeshAttributeType.F32: 4,
        MeshAttributeType.U8: 1,
        MeshAttributeType.I8: 1,
        MeshAttributeType.U16: 2,
        MeshAttributeType.I16: 2,
        MeshAttributeType.U32: 4,
        MeshAttributeType.I32: 4,
    }[value]


def _bindAttributes(attributes: tuple[MeshAttribute, ...]) -> None:
    stride = 0
    for index, attribute in enumerate(attributes):
        stride += _sizeOfMeshAttributeType(attribute.type) * attribute.dimensions

    offset = 0
    for index, attribute in enumerate(attributes):
        glVertexAttribPointer(attribute.location, attribute.dimensions.value, attribute.type.value, False, stride, ctypes.c_void_p(offset))
        glEnableVertexAttribArray(attribute.location)
        offset += _sizeOfMeshAttributeType(attribute.type) * attribute.dimensions


def _get_pixels(texture: int) -> ctypes.Array[ctypes.c_float]:
    glBindTexture(GL_TEXTURE_2D, texture)
    width = glGetTexLevelParameteriv(GL_TEXTURE_2D, 0, GL_TEXTURE_WIDTH)
    height = glGetTexLevelParameteriv(GL_TEXTURE_2D, 0, GL_TEXTURE_HEIGHT)
    pixels = (ctypes.c_float * (width * height * 4))()
    glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_FLOAT, pixels)
    return pixels


class Evaluator:
    def __init__(self, projectShadersFolder: str) -> None:
        # Framebuffers & color buffers
        self._fbos: dict[str, int] = {}
        self._fboCbos: dict[str, list[int]] = {}

        # Shader storage buffers
        self._ssbos: dict[str, int] = {}

        self._project: Optional[Project] = None

        # Shader
        self._programs = ProgramPool()

        # Full screen quad helpers
        self._rectVao: int = 0
        self._meshVao: int = 0
        self._rectVert: int = 0

        # Back buffer info
        self._screenWidth: int = 0
        self._screenHeight: int = 0
        self._backbuffer: int = 0

        # TODO: Preferably these are all moved out of the evaluator.
        self._commandEvaluators = {
            BindFramebuffer: self._bindFramebuffer,
            Clear: self._clear,
            DrawRect: self._drawRect,
            DrawMesh: self._drawMesh,
            DispatchCompute: self._dispatchCompute
        }

        self._projectShaderFolder = projectShadersFolder
        self._activeShaderFolders: tuple[str, ...] = tuple()

    def cleanup(self) -> None:
        glDeleteFramebuffers(len(self._fbos), list(self._fbos.values()))
        for cbos in self._fboCbos.values():
            glDeleteTextures(len(cbos), cbos)
        glDeleteBuffers(len(self._ssbos), list(self._ssbos.values()))
        self._fbos.clear()
        self._fboCbos.clear()
        self._ssbos.clear()
        self._project = None
        glDeleteVertexArrays(1, (self._rectVao,))
        glDeleteVertexArrays(1, (self._meshVao,))
        glDeleteShader(self._rectVert)

    def _initialize_framebuffers(self, screenWidth, screenHeight):
        # Generate the FBOs
        fbos = glGenFramebuffers(len(self._project.framebuffers))
        if isinstance(fbos, int):
            fbos = [fbos]

        for (framebufferName, framebuffer), fbo in zip(self._project.framebuffers.items(), fbos):
            self._fbos[framebufferName] = fbo
            glBindFramebuffer(GL_FRAMEBUFFER, fbo)

            # Generate the CBOs
            assert framebuffer.outputs, ('Framebuffer with 0 outputs: ', framebuffer)
            cbos = glGenTextures(framebuffer.outputs)
            if isinstance(cbos, int):
                cbos = [cbos]
            self._fboCbos[framebufferName] = cbos

            assert framebuffer.width >= 0 and framebuffer.height >= 0 and framebuffer.factor >= 0
            assert (framebuffer.width > 0 and framebuffer.height > 0) != (framebuffer.factor > 0)

            # Allocate the CBOs and bind them to the FBO
            width = screenWidth // framebuffer.factor if framebuffer.factor else framebuffer.width
            height = screenHeight // framebuffer.factor if framebuffer.factor else framebuffer.height

            for cboIndex in range(framebuffer.outputs):
                cbo = self._fboCbos[framebufferName][cboIndex]
                glBindTexture(GL_TEXTURE_2D, cbo)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA32F, width, height, 0, GL_RGBA, GL_FLOAT, None)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                # glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
                # glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
                glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0 + cboIndex, GL_TEXTURE_2D, cbo, 0)

            if framebuffer.depth:
                rbo = glGenRenderbuffers(1)
                glBindRenderbuffer(GL_RENDERBUFFER, rbo)
                glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT, width, height)
                glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, rbo)

            assert glCheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE

    def _initialize_storagebuffers(self):
        ssbos = glGenBuffers(len(self._project.storagebuffers))
        if isinstance(ssbos, int):
            ssbos = [ssbos]

        for (storagebufferName, storagebuffer), ssbo in zip(self._project.storagebuffers.items(), ssbos):
            self._ssbos[storagebufferName] = ssbo
            glBindBuffer(GL_SHADER_STORAGE_BUFFER, ssbo)
            glBufferData(GL_SHADER_STORAGE_BUFFER, storagebuffer.sizeInBytes, None, GL_STATIC_DRAW)

    def initialize(self, project: Project, screenWidth: int, screenHeight: int, projectShadersFolder: str) -> None:
        # Reset & rebuild
        self.cleanup()
        self._project = project
        self._projectShaderFolder = projectShadersFolder

        if project.framebuffers:
            self._initialize_framebuffers(screenWidth, screenHeight)

        if project.storagebuffers:
            self._initialize_storagebuffers()

        # Generate reusable resoures
        self._rectVao = glGenVertexArrays(1)
        self._meshVao = glGenVertexArrays(1)  # TODO: Not sure if needed
        self._rectVert = shaders.compileShader('#version 410\nout vec2 vUV;void main(){gl_Position=vec4(step(1,gl_VertexID)*step(-2,-gl_VertexID)*2-1,gl_VertexID-gl_VertexID%2-1,0,1);vUV=gl_Position.xy*.5+.5;}', GL_VERTEX_SHADER)
        self._screenWidth = screenWidth
        self._screenHeight = screenHeight

        # Set GL state
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        # Having a clear color is useful for debugging:
        glClearColor(0.0, 0.5, 0.0, 1.0)

        # Run initialization commands
        self.draw(self._project.staticDraw)

    def setBackbuffer(self, fbo: int) -> None:
        self._backbuffer = fbo

    def resize(self, screenWidth: int, screenHeight: int) -> None:
        if self._project is None:
            return

        # TODO: This gets called on window close after the context has already invalidated all handles, causing an error on exit.

        # Store new size
        self._screenWidth = screenWidth
        self._screenHeight = screenHeight

        # Resize fbos
        for framebufferName, framebuffer in self._project.framebuffers.items():
            if not framebuffer.factor:
                continue
            for cbo in self._fboCbos[framebufferName]:
                glBindTexture(GL_TEXTURE_2D, cbo)
                width = screenWidth // framebuffer.factor
                height = screenHeight // framebuffer.factor
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA32F, width, height, 0, GL_RGBA, GL_FLOAT, None)

        # In case the project initializes static textures at screen resolution, re-initialize those
        self.draw(self._project.staticDraw)

    def draw(self, commands: tuple[Command, ...], *shaderFolders: str) -> None:
        self._activeShaderFolders = (self._projectShaderFolder,) + shaderFolders
        for command in commands:
            self._commandEvaluators[command.__class__](command)  # type: ignore
        self._activeShaderFolders = tuple()

    def _bindFramebuffer(self, command: BindFramebuffer) -> None:
        if command.framebuffer:
            glBindFramebuffer(GL_FRAMEBUFFER, self._fbos[command.framebuffer])
            framebuffer = self._project.framebuffers[command.framebuffer]
            width = self._screenWidth // framebuffer.factor if framebuffer.factor else framebuffer.width
            height = self._screenHeight // framebuffer.factor if framebuffer.factor else framebuffer.height
            glViewport(0, 0, width, height)
            attachments = tuple(GL_COLOR_ATTACHMENT0 + i for i in range(framebuffer.outputs))
            glDrawBuffers(len(attachments), attachments)
        else:
            glBindFramebuffer(GL_FRAMEBUFFER, 0)
            glViewport(0, 0, self._screenWidth, self._screenHeight)

    @staticmethod
    def _clear(command: Clear) -> None:
        bits = 0
        if command.depth:
            bits |= GL_DEPTH_BUFFER_BIT
        if command.color:
            bits |= GL_COLOR_BUFFER_BIT
        glClear(bits)

    def setUniforms(self) -> None:
        # TODO: placeholder.
        pass

    def _useProgram(self, program: int, command: DrawRect) -> None:
        glUseProgram(program)

        # TODO: Forward the set uniforms.

        # Set target resolution
        view = glGetIntegerv(GL_VIEWPORT)
        glUniform2f(glGetUniformLocation(program, 'uResolution'), view[2], view[3])

        # Set image inputs
        for uniformIndex, (framebufferName, cboIndex) in enumerate(command.textures):
            glActiveTexture(GL_TEXTURE0 + uniformIndex)
            texture = self._fboCbos[framebufferName][cboIndex]
            glBindTexture(GL_TEXTURE_2D, texture)
            '''
            # Debug: check if the buffer has data
            framebuffer = self._project.framebuffers[framebufferName]
            width = self._screenWidth // framebuffer.factor if framebuffer.factor else framebuffer.width
            height = self._screenHeight // framebuffer.factor if framebuffer.factor else framebuffer.height
            data = (ctypes.c_float * (4 * width * height))()
            glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_FLOAT, data)
            print(data[0], data[1], data[2], data[3])
            '''
            loc = glGetUniformLocation(program, f'uImages[{uniformIndex}]')
            glUniform1i(loc, uniformIndex)

    def _drawRect(self, command: DrawRect) -> None:
        program = self._programs.program(self._rectVert, (command.resolvedFragment(*self._activeShaderFolders), GL_FRAGMENT_SHADER))
        self._useProgram(program, command)

        glBindVertexArray(self._rectVao)
        glDrawArrays(GL_TRIANGLE_FAN, 0, 4)

    def _drawMesh(self, command: DrawMesh) -> None:
        glBindVertexArray(self._meshVao)

        shaderArgs = []
        if command.vertex:
            shaderArgs.append((command.resolvedVertex(*self._activeShaderFolders), GL_VERTEX_SHADER))
        if command.geometry:
            shaderArgs.append((command.resolvedGeometry(*self._activeShaderFolders), GL_GEOMETRY_SHADER))
        if command.fragment:
            shaderArgs.append((command.resolvedFragment(*self._activeShaderFolders), GL_FRAGMENT_SHADER))

        program = self._programs.program(*shaderArgs)
        self._useProgram(program, command)

        if command.vbo:
            ssbo = self._ssbos[command.vbo]
            glBindBuffer(GL_ARRAY_BUFFER, ssbo)
            '''
            # Debug: check if the buffer has data
            data = (ctypes.c_float * (3 * 1000))()
            glGetBufferSubData(GL_ARRAY_BUFFER, 0, 4 * 3 * 1000, data)
            for xyz in zip(data[0::3],data[1::3],data[2::3]):
                print(xyz)
            '''
            _bindAttributes(self._project.meshLayouts[command.layout].attributes)

        if command.ivbo:
            ssbo = self._ssbos[command.ivbo]
            glBindBuffer(GL_ARRAY_BUFFER, ssbo)
            _bindAttributes(self._project.meshLayouts[command.layout].instanceAttributes)

        if command.ibo:
            ssbo = self._ssbos[command.ibo]
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ssbo)
            if command.instanceCount:
                glDrawElementsInstanced(command.primitive.value, command.count, GL_UNSIGNED_INT, None, command.instanceCount)
            else:
                glDrawElements(command.primitive.value, command.count, GL_UNSIGNED_INT, None)
        else:
            if command.instanceCount > 1:
                glDrawArraysInstanced(command.primitive.value, 0, command.count, command.instanceCount)
            else:
                glDrawArrays(command.primitive.value, 0, command.count)

    def _dispatchCompute(self, command: DispatchCompute) -> None:
        program = self._programs.program((command.resolvedCompute(*self._activeShaderFolders), GL_COMPUTE_SHADER))
        glUseProgram(program)

        for binding, name in enumerate(command.storagebuffers):
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, binding, self._ssbos[name])

        glDispatchCompute(*command.groups)
        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)

        '''
        # Debug: check if the buffer was updated
        for binding, name in enumerate(command.storagebuffers):
            data = (ctypes.c_float * (3 * 1000))()
            index = self._ssboNameToIndex[name]
            glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.ssbos[index])
            glGetBufferSubData(GL_SHADER_STORAGE_BUFFER, 0, 4 * 3 * 1000, data)
        '''


def main():
    with open('test_project/project.json5', 'rb') as fh:
        project = Project(**tt_json5.parse(tt_json5.SStream(fh.read())))

    with open('test_project/template.json5', 'rb') as fh:
        template = Template(**tt_json5.parse(tt_json5.SStream(fh.read())))

    app = QApplication([])
    win = QOpenGLWindow()
    ev = Evaluator()
    win.initializeGL = lambda: ev.initialize(project, win.width(), win.height())
    win.resizeEvent = lambda _: ev.resize(win.width(), win.height())
    win.paintGL = lambda: ev.draw(template.draw)
    win.closeEvent = lambda: ev.cleanup()
    ev.setBackbuffer(win.defaultFramebufferObject())  # TODO: What if this changes?
    win.show()
    app.exec()


if __name__ == '__main__':
    main()
