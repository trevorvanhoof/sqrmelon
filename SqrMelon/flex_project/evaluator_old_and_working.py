import os
from typing import Union

from OpenGL.GL import *
from OpenGL.GL import shaders
from PySide6.QtOpenGL import QOpenGLWindow
from PySide6.QtWidgets import QApplication

from flex_project.utils import tt_json5
from flex_project.structure_old_and_working import BindFramebuffer, Clear, Command, DispatchCompute, DrawMesh, DrawRect, MeshAttribute, MeshAttributeType, MeshLayout, Project, Template


def _sizeOfMeshAttributeType(value: MeshAttributeType) -> int:
    return {
        MeshAttributeType.F32: 4,
        MeshAttributeType.F16: 2,
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
        glVertexAttribPointer(index, attribute.dimensions.value, attribute.type.value, False, stride, ctypes.c_void_p(offset))
        glEnableVertexAttribArray(index)
        offset += _sizeOfMeshAttributeType(attribute.type) * attribute.dimensions


class ProgramPool:
    def __init__(self) -> None:
        self._shaders: dict[tuple[str, int], int] = {}
        self._programs: dict[tuple[int, ...], int] = {}

    def shader(self, paths: tuple[str, ...], shaderType: int) -> int:
        # TODO: File watching
        key = ''.join(paths), shaderType
        if key in self._shaders:
            return self._shaders[key]
        stitches = []
        for path in paths:
            shaders_path = 'test_assets/shaders/' + path
            template_path = 'test_assets/templates/example/' + path.lstrip('_')
            if os.path.exists(shaders_path):
                template_path = shaders_path
            with open(template_path) as fh:
                stitches.append(fh.read())
        inst = shaders.compileShader('\n'.join(stitches), shaderType)
        self._shaders[key] = inst
        return inst

    def program(self, *shaderArgs: Union[int, tuple[tuple[str, ...], int]]) -> int:
        instances = []
        for element in shaderArgs:
            if isinstance(element, int):
                instances.append(element)
            else:
                paths, shaderType = element
                instances.append(self.shader(paths, shaderType))
        key = tuple(instances)
        if key in self._programs:
            return self._programs[key]
        inst = shaders.compileProgram(*instances)
        self._programs[key] = inst
        return inst


def _get_pixels(texture: int) -> ctypes.Array[ctypes.c_float]:
    glBindTexture(GL_TEXTURE_2D, texture)
    width = glGetTexLevelParameteriv(GL_TEXTURE_2D, 0, GL_TEXTURE_WIDTH)
    height = glGetTexLevelParameteriv(GL_TEXTURE_2D, 0, GL_TEXTURE_HEIGHT)
    pixels = (ctypes.c_float * (width * height * 4))()
    glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_FLOAT, pixels)
    return pixels


class Evaluator:
    def __init__(self) -> None:
        # Framebuffers & color buffers
        self.fbos: list[int] = []
        self.cbos: list[int] = []

        # Shader storage buffers
        self.ssbos: list[int] = []

        # TODO: All this extra state is bad design
        #  can't we just store the project and make fbos & ssbos dicts instead?
        self._fboNameToIndex: dict[str, int] = {}
        self._factoredCbos: list[tuple[int, int, int]] = []
        self._fboDrawBuffers: list[list[int]] = []
        self._fboSizes: list[tuple[int, int]] = []
        self._fboCbos: list[list[int]] = []
        self._ssboNameToIndex: dict[str, int] = {}
        self._staticDraw: tuple[Command, ...] = tuple()
        # Meshes
        self._namedMeshLayouts: dict[str, MeshLayout] = {}

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

    def cleanup(self) -> None:
        glDeleteFramebuffers(len(self.fbos), self.fbos)
        glDeleteTextures(len(self.cbos), self.cbos)
        glDeleteBuffers(len(self.ssbos), self.ssbos)
        self.fbos.clear()
        self.cbos.clear()
        self.ssbos.clear()
        self._fboNameToIndex.clear()
        self._factoredCbos.clear()
        self._fboDrawBuffers.clear()
        self._fboSizes.clear()
        self._fboCbos.clear()
        self._ssboNameToIndex.clear()
        self._staticDraw = tuple()
        self._namedMeshLayouts.clear()
        glDeleteVertexArrays(1, (self._rectVao,))
        glDeleteVertexArrays(1, (self._meshVao,))
        glDeleteShader(self._rectVert)

    def initialize(self, project: Project, screenWidth: int, screenHeight: int) -> None:
        self.cleanup()

        if len(project.framebuffers):
            self.fbos = glGenFramebuffers(len(project.framebuffers))
            if isinstance(self.fbos, int):
                self.fbos = [self.fbos]
        cboCount = sum(fbo.outputs for fbo in project.framebuffers)
        if cboCount:
            self.cbos = glGenTextures(cboCount)
            if isinstance(self.cbos, int):
                self.cbos = [self.cbos]

        cursor = 0
        for fboIndex, framebuffer in enumerate(project.framebuffers):
            glBindFramebuffer(GL_FRAMEBUFFER, self.fbos[fboIndex])
            self._fboDrawBuffers.append([])
            width = screenWidth // framebuffer.factor if framebuffer.factor else framebuffer.width
            height = screenHeight // framebuffer.factor if framebuffer.factor else framebuffer.height
            self._fboSizes.append((width, height))
            self._fboCbos.append([])
            for cboIndex in range(framebuffer.outputs):
                cbo = self.cbos[cursor]
                glBindTexture(GL_TEXTURE_2D, cbo)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA32F, width, height, 0, GL_RGBA, GL_FLOAT, None)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                # glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
                # glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
                glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0 + cboIndex, GL_TEXTURE_2D, cbo, 0)
                if framebuffer.factor:
                    self._factoredCbos.append((fboIndex, cboIndex, framebuffer.factor))
                self._fboDrawBuffers[-1].append(GL_COLOR_ATTACHMENT0 + cboIndex)
                self._fboCbos[-1].append(cbo)
                cursor += 1
            assert glCheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE

        if len(project.storagebuffers):
            self.ssbos = glGenBuffers(len(project.storagebuffers))
            if not isinstance(self.ssbos, list):
                self.ssbos = [self.ssbos]
            for ssboIndex, storagebuffer in enumerate(project.storagebuffers):
                glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.ssbos[ssboIndex])
                glBufferData(GL_SHADER_STORAGE_BUFFER, storagebuffer.sizeInBytes, None, GL_STATIC_DRAW)

        self._fboNameToIndex = {fbo.name: i for i, fbo in enumerate(project.framebuffers)}
        self._ssboNameToIndex = {ssbo.name: i for i, ssbo in enumerate(project.storagebuffers)}
        self._namedMeshLayouts = {layout.name: layout for layout in project.meshLayouts}

        self._rectVao = glGenVertexArrays(1)
        self._meshVao = glGenVertexArrays(1)
        self._rectVert = shaders.compileShader('#version 410\nout vec2 vUV;void main(){gl_Position=vec4(step(1,gl_VertexID)*step(-2,-gl_VertexID)*2-1,gl_VertexID-gl_VertexID%2-1,0,1);vUV=gl_Position.xy*.5+.5;}', GL_VERTEX_SHADER)
        self._screenWidth = screenWidth
        self._screenHeight = screenHeight

        self._staticDraw = project.staticDraw
        self.draw(self._staticDraw)

        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        # Having a clear color is useful for debugging:
        glClearColor(0.0, 0.5, 0.0, 1.0)

    def setBackbuffer(self, fbo: int) -> None:
        self._backbuffer = fbo

    def resize(self, screenWidth: int, screenHeight: int) -> None:
        # TODO: This gets called on window close after the context has already invalidated all handles, causing an error on exit.
        for fboIndex, cboIndex, factor in self._factoredCbos:
            glBindTexture(GL_TEXTURE_2D, self._fboCbos[fboIndex][cboIndex])
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA32F, screenWidth // factor, screenHeight // factor, 0, GL_RGBA, GL_FLOAT, None)
            self._fboSizes[fboIndex] = screenWidth // factor, screenHeight // factor
        self._screenWidth = screenWidth
        self._screenHeight = screenHeight

        self.draw(self._staticDraw)

    def draw(self, commands: tuple[Command, ...]) -> None:
        for command in commands:
            self._commandEvaluators[command.__class__](command)

    def _bindFramebuffer(self, command: BindFramebuffer) -> None:
        if command.framebuffer:
            index = self._fboNameToIndex[command.framebuffer]
            glBindFramebuffer(GL_FRAMEBUFFER, self.fbos[index])
            width, height = self._fboSizes[index]
            glViewport(0, 0, width, height)
            glDrawBuffers(len(self._fboDrawBuffers[index]), self._fboDrawBuffers[index])
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
        for uniformIndex, (framebuffer, cboIndex) in enumerate(command.textures):
            glActiveTexture(GL_TEXTURE0 + uniformIndex)
            fboIndex = self._fboNameToIndex[framebuffer]
            texture = self._fboCbos[fboIndex][cboIndex]
            glBindTexture(GL_TEXTURE_2D, texture)
            loc = glGetUniformLocation(program, f'uImages[{uniformIndex}]')
            glUniform1i(loc, uniformIndex)

    def _drawRect(self, command: DrawRect) -> None:
        program = self._programs.program(self._rectVert, (command.fragment, GL_FRAGMENT_SHADER))
        self._useProgram(program, command)

        glBindVertexArray(self._rectVao)
        glDrawArrays(GL_TRIANGLE_FAN, 0, 4)

    def _drawMesh(self, command: DrawMesh) -> None:
        glBindVertexArray(self._meshVao)

        shaderArgs = []
        if command.vertex:
            shaderArgs.append((command.vertex, GL_VERTEX_SHADER))
        if command.geometry:
            shaderArgs.append((command.geometry, GL_GEOMETRY_SHADER))
        if command.fragment:
            shaderArgs.append((command.fragment, GL_FRAGMENT_SHADER))

        program = self._programs.program(*shaderArgs)
        self._useProgram(program, command)

        if command.vbo:
            ssbo = self.ssbos[self._ssboNameToIndex[command.vbo]]
            glBindBuffer(GL_ARRAY_BUFFER, ssbo)
            '''
            # Debug: check if the buffer has data
            data = (ctypes.c_float * (3 * 1000))()
            glGetBufferSubData(GL_ARRAY_BUFFER, 0, 4 * 3 * 1000, data)
            for xyz in zip(data[0::3],data[1::3],data[2::3]):
                print(xyz)
            '''
            _bindAttributes(self._namedMeshLayouts[command.layout].attributes)

        if command.ivbo:
            ssbo = self.ssbos[self._ssboNameToIndex[command.ivbo]]
            glBindBuffer(GL_ARRAY_BUFFER, ssbo)
            _bindAttributes(self._namedMeshLayouts[command.layout].instanceAttributes)

        if command.ibo:
            ssbo = self.ssbos[self._ssboNameToIndex[command.ibo]]
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
        program = self._programs.program((command.compute, GL_COMPUTE_SHADER))
        glUseProgram(program)

        for binding, name in enumerate(command.storagebuffers):
            index = self._ssboNameToIndex[name]
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, binding, self.ssbos[index])

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
    with open('project_old_and_working.json5', 'rb') as fh:
        project = Project(**tt_json5.parse(tt_json5.SStream(fh.read())))

    with open('test_project/templates/example.json5', 'rb') as fh:
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


main()
