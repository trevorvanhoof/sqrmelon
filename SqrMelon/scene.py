import sys
import re
import time
from collections import OrderedDict
from fileutil import FileSystemWatcher, FilePath
from profileui import Profiler
from multiplatformutil import canValidateShaders

from OpenGL.GL import shaders
from OpenGL.GL.EXT import texture_filter_anisotropic

from heightfield import loadHeightfield
from buffers import *
from qtutil import *
from util import currentProjectFilePath, parseXMLWithIncludes, currentProjectDirectory, templatePathFromScenePath
from gl_shaders import compileProgram


class TexturePool(object):
    """
    Utility to fetch & bind textures by file path, loaded only once.
    File paths are treated slash and case insensitive.
    """
    __cache = {}

    @staticmethod
    def fetchAndUse(fileName):
        assert not '\\' in fileName

        key = fileName.lower().replace('//', '/')
        if key in TexturePool.__cache:
            glBindTexture(GL_TEXTURE_2D, TexturePool.__cache[key])
            return TexturePool.__cache[key]
        parentPath = currentProjectDirectory()
        fullName = parentPath.join(fileName)

        # texture is a single channel raw32 heightmap
        if fileName.endswith('.r32'):
            tex = loadHeightfield(fullName)
            TexturePool.__cache[key] = tex._id
            return tex._id

        # read file into openGL texture
        img = QImage(fullName)
        if img.isNull():
            print 'Warning, could not load texture %s.' % fullName
            TexturePool.__cache[key] = 0  # no texture
            return 0
        img = QGLWidget.convertToGLFormat(img)
        tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width(), img.height(), 0, GL_RGBA, GL_UNSIGNED_BYTE, ctypes.c_void_p(int(img.bits())))
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        TexturePool.__cache[key] = tex
        return tex


class PassData(object):
    def __init__(self,
                 vertStitches,
                 fragStitches,
                 uniforms,
                 inputBufferIds=None,
                 targetBufferId=-1,
                 realtime=None,
                 resolution=None,
                 tile=False,
                 downSampleFactor=None,
                 numOutputBuffers=1,
                 drawCommand=None,
                 is3d=False,
                 name=None):
        self.vertStitches = vertStitches
        self.fragStitches = fragStitches
        self.uniforms = uniforms
        self.inputBufferIds = inputBufferIds or []
        self.targetBufferId = targetBufferId
        self.realtime = realtime
        # buffer data
        self.resolution = resolution
        self.tile = tile
        self.downSampleFactor = downSampleFactor
        self.numOutputBuffers = numOutputBuffers
        self.drawCommand = drawCommand
        if is3d:
            assert not realtime, '3D textures can not be updated in real time.'
            assert not drawCommand, '3D textures can not be rendered using  custom drawing code.'
        self.is3d = is3d
        self.name = name


def _deserializePasses(sceneFile):
    """
    :type sceneFile: FilePath
    :rtype: list[PassData]
    """
    assert isinstance(sceneFile, FilePath)
    sceneDir = sceneFile.stripExt()
    templatePath = templatePathFromScenePath(sceneFile)
    templateDir = templatePath.stripExt()
    xTemplate = parseXMLWithIncludes(templatePath)
    passes = []
    frameBufferMap = {}
    for xPass in xTemplate:
        buffer = -1
        if 'buffer' in xPass.attrib:
            buffer = xPass.attrib['buffer']
            if buffer not in frameBufferMap:
                frameBufferMap[buffer] = len(frameBufferMap)

        size = None
        if 'size' in xPass.attrib:
            size = int(xPass.attrib['size']), int(xPass.attrib['size'])
        elif 'width' in xPass.attrib and 'height' in xPass.attrib:
            size = int(xPass.attrib['width']), int(xPass.attrib['height'])

        tile = size is not None
        if 'tile' in xPass.attrib:
            tile = xPass.attrib['tile'].lower() == 'true'

        factor = None
        if 'factor' in xPass.attrib:
            factor = int(xPass.attrib['factor'])

        realtime = int(xPass.attrib.get('static', 0)) == 0

        is3d = int(xPass.attrib.get('is3d', 0)) != 0
        if is3d:
            assert (size[0] ** 0.5) == size[1]
            size = size[0], size[1]

        outputs = int(xPass.attrib.get('outputs', 1))

        inputs = []
        i = 0
        key = 'input%s' % i
        while key in xPass.attrib:
            # input is filename?
            parentPath = currentProjectFilePath()
            fullName = parentPath.join(xPass.attrib[key])
            if fullName.exists():
                inputs.append(FilePath(xPass.attrib[key]))
            else:
                # input is buffer
                if '.' in xPass.attrib[key]:
                    frameBuffer, subTexture = xPass.attrib[key].split('.')
                    frameBuffer, subTexture = frameBuffer, int(subTexture)
                else:
                    frameBuffer, subTexture = xPass.attrib[key], 0

                if frameBuffer not in frameBufferMap:
                    frameBufferMap[frameBuffer] = len(frameBufferMap)
                inputs.append((frameBufferMap[frameBuffer], subTexture))

            i += 1
            key = 'input%s' % i
        vertStitches = []
        fragStitches = []
        uniforms = {}
        for xElement in xPass:
            path = FilePath(xElement.attrib['path'])
            stitches = vertStitches if path.hasExt('vert') else fragStitches
            if xElement.tag.lower() == 'section':
                stitches.append(sceneDir.join(path))
            elif xElement.tag.lower() in ('shared', 'global'):
                stitches.append(templateDir.join(path))
            else:
                raise ValueError('Unknown XML tag in pass: "%s"' % xElement.tag)
            for xUniform in xElement:
                uniforms[xUniform.attrib['name']] = [float(x.strip()) for x in xUniform.attrib['value'].split(',')]

        passes.append(PassData(vertStitches, fragStitches, uniforms, inputs, frameBufferMap.get(buffer, -1), realtime, size, tile, factor, outputs, xPass.attrib.get('drawcommand', None), is3d, xPass.attrib.get('name', None)))
    return passes


class CameraTransform(object):
    def __init__(self, tx=0, ty=0, tz=0, rx=0, ry=0, rz=0):
        self.data = [tx, ty, tz, rx, ry, rz]

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        return self.data[index]

    def __setitem__(self, index, value):
        self.data[index] = value

    @property
    def translate(self):
        return tuple(self.data[:3])

    @property
    def rotate(self):
        return tuple(self.data[3:6])

    @translate.setter
    def translate(self, translate):
        self.data[:3] = translate

    @rotate.setter
    def rotate(self, rotate):
        self.data[3:6] = rotate


class _ShaderPool(object):
    def __init__(self):
        self.__cache = {}

    def compileProgram(self, vertCode, fragCode):
        """
        A compileProgram version that ensures we don't recompile unnecessarily.
        """
        program = self.__cache.get((vertCode, fragCode), None)
        if program:
            return program
        program = compileProgram(
            shaders.compileShader(vertCode, GL_VERTEX_SHADER),
            shaders.compileShader(fragCode, GL_FRAGMENT_SHADER),
            validate=canValidateShaders()
        )
        self.__cache[(vertCode, fragCode)] = program
        return program


gShaderPool = _ShaderPool()


def _loadGLSLWithIncludes(glslPath, ioIncludePaths):
    assert isinstance(glslPath, FilePath)
    search = re.compile(r'(?![^/*]*\*/)^[\t ]*(#include "[a-z0-9_]+")[\t ]*$', re.MULTILINE | re.IGNORECASE | re.DOTALL)
    text = glslPath.content()
    for res in list(search.finditer(text)):
        inc = res.group(1)
        idx = inc.find('"') + 1
        name = inc[idx:inc.find('"', idx + 1)]
        path = glslPath.join('..', name).abs().lower()
        assert path not in ioIncludePaths, 'Recursive or duplicate include "%s" found while parsing "%s"' % (path, glslPath)
        ioIncludePaths.add(path)
        text = '\n'.join([text[:res.start(1)], _loadGLSLWithIncludes(path, ioIncludePaths), text[res.end(1):]])
    return text


class FullScreenRectSingleton(object):
    _instance = None

    def __init__(self):
        self._vao = glGenVertexArrays(1)

    def draw(self):
        # I don't bind anything, no single buffer or VAO is generated, there are no geometry shaders and no transform feedback systems
        # according to the docs there is no reason why glDrawArrays wouldn't work.
        glBindVertexArray(self._vao)  # glBindVertexArray(0) doesn't work either
        glDrawArrays(GL_TRIANGLE_FAN, 0, 4)

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


class Scene(object):
    cache = {}
    passThroughProgram = None
    STATIC_VERT = '#version 410\nout vec2 vUV;void main(){gl_Position=vec4(step(1,gl_VertexID)*step(-2,-gl_VertexID)*2-1,gl_VertexID-gl_VertexID%2-1,0,1);vUV=gl_Position.xy*.5+.5;}'
    PASS_THROUGH_FRAG = '#version 410\nin vec2 vUV;uniform vec4 uColor;uniform sampler2D uImages[1];out vec4 outColor0;void main(){outColor0=uColor*texture(uImages[0], vUV);}'

    @classmethod
    def drawColorBufferToScreen(cls, colorBuffer, viewport, color=(1.0, 1.0, 1.0, 1.0)):
        FrameBuffer.clear()

        passThrough = Scene.usePassThroughProgram(color)
        glActiveTexture(GL_TEXTURE0)

        colorBuffer.use()

        glUniform1i(glGetUniformLocation(passThrough, 'uImages[0]'), 0)
        glViewport(*viewport)

        FullScreenRectSingleton.instance().draw()

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, 0)

    @classmethod
    def getPassThroughProgram(cls):
        if cls.passThroughProgram:
            return cls.passThroughProgram
        cls.passThroughProgram = gShaderPool.compileProgram(cls.STATIC_VERT, cls.PASS_THROUGH_FRAG)
        return cls.passThroughProgram

    @classmethod
    def usePassThroughProgram(cls, color=(1.0, 1.0, 1.0, 1.0)):
        passThrough = cls.getPassThroughProgram()
        glUseProgram(passThrough)
        glUniform4f(glGetUniformLocation(passThrough, 'uColor'), *color)
        return passThrough

    @classmethod
    def getScene(cls, sceneFile):
        assert isinstance(sceneFile, FilePath)
        # avoid compiler hick-ups during playback by caching the scenes once they were compiled
        if sceneFile in cls.cache:
            return cls.cache[sceneFile]
        return cls(sceneFile)

    def __init__(self, sceneFile):
        assert isinstance(sceneFile, FilePath)
        Scene.cache[sceneFile] = self
        self.__w = 0
        self.__h = 0

        self._debugPassId = None

        self.shaders = []
        self.frameBuffers = []
        self.colorBuffers = []
        self.profileLog = []
        self.profileInfoChanged = Signal()

        self.__filePath = sceneFile
        self.fileSystemWatcher_scene = FileSystemWatcher()
        self.fileSystemWatcher_scene.fileChanged.connect(self._reload)
        templatePath = templatePathFromScenePath(sceneFile)
        self.fileSystemWatcher_scene.addPath(templatePath)

        self.__errorDialog = QDialog()  # error log
        self.__errorDialog.setWindowTitle('Compile log')
        self.__errorDialog.setLayout(vlayout())
        self.__errorDialogText = QTextEdit()
        self.__errorDialog.layout().addWidget(self.__errorDialogText)
        hbar = hlayout()
        self.__errorDialog.layout().addLayout(hbar)
        hbar.addStretch(1)
        btn = QPushButton('Close')
        hbar.addWidget(btn)
        btn.clicked.connect(self.__errorDialog.accept)

        self._reload(None)

    def setDebugPass(self, nameOrId=None, colorBuffer=0):
        self._debugPassId = None
        for i, passData in enumerate(self.passes):
            if passData.name == nameOrId or i == nameOrId:
                self._debugPassId = i, colorBuffer
                return

    def _reload(self, path):
        if path:
            assert isinstance(path, FilePath)
            time.sleep(0.01)
            if not path.exists():
                # the scene has been deleted, stop watching it
                return
            self.fileSystemWatcher_scene.addPath(path)

        self.passes = _deserializePasses(self.__filePath)

        self.fileSystemWatcher = FileSystemWatcher()
        self.fileSystemWatcher.fileChanged.connect(self._rebuild)
        watched = set()
        for passData in self.passes:
            newStitches = (set(passData.vertStitches) | set(passData.fragStitches)) - watched
            if newStitches:
                self.fileSystemWatcher.addPaths(list(newStitches))
                watched |= newStitches

        self._rebuild(None)
        self.__cameraData = None

    def _rebuild(self, path, index=None):
        if path:
            assert isinstance(path, FilePath)
            time.sleep(0.01)
            if not path.exists():
                # the scene has been deleted, stop watching it
                return
            self.fileSystemWatcher.addPath(path)
            path = path.abs()

        for i, passData in enumerate(self.passes):
            vert = True
            frag = True

            # make sure the changed path is in our dependencies
            if path:
                if not path in (stitch.abs() for stitch in passData.vertStitches):
                    vert = False
                if not path in (stitch.abs() for stitch in passData.fragStitches):
                    frag = False
                if not vert and not frag:
                    continue

            if index is not None and index != i:
                continue

            includePaths = set()
            errors = []

            vertCode = []
            for stitch in passData.vertStitches:
                try:
                    vertCode.append(_loadGLSLWithIncludes(stitch, includePaths))
                except IOError as e:
                    errors.append(stitch.abs())

            fragCode = []
            for stitch in passData.fragStitches:
                try:
                    fragCode.append(_loadGLSLWithIncludes(stitch, includePaths))
                except IOError as e:
                    errors.append(stitch.abs())

            if errors:
                QMessageBox.critical(None, 'Missing files', 'A template or scene could not be loaded & is missing the following files:\n\n%s' % '\n'.join(errors))
                return

            if includePaths:
                self.fileSystemWatcher.addPaths(list(includePaths))

            # not joining causes "unexpected $undefined" errors during shader compilation,
            # no idea why it injects invalid bytes
            if not vertCode:
                vertCode = Scene.STATIC_VERT
            else:
                vertCode = '\n'.join(vertCode)

            fragCode = '\n'.join(fragCode)

            try:
                program = gShaderPool.compileProgram(vertCode, fragCode)

            except RuntimeError, e:
                self.shaders = []
                errors = e.args[0].split('\n')
                try:
                    code = e.args[1][0].split('\n')
                except:
                    print e.args
                    print 'pass: ' + passData.name
                    print 'fragCode:'
                    print fragCode
                    return
                # html escape output
                errors = [Qt.escape(ln) for ln in errors]
                code = [Qt.escape(ln) for ln in code]
                log = []
                for error in errors:
                    try:
                        lineNumber = int(error.split(' : ', 1)[0].rsplit('(')[-1].split(')')[0])
                    except:
                        continue
                    lineNumber -= 1
                    log.append('<p><font color="red">%s</font><br/>%s<br/><font color="#081">%s</font><br/>%s</p>' % (
                        error, '<br/>'.join(code[lineNumber - 5:lineNumber]), code[lineNumber], '<br/>'.join(code[lineNumber + 1:lineNumber + 5])))
                self.__errorDialogText.setHtml('<pre>' + '\n'.join(log) + '</pre>')
                self.__errorDialog.setGeometry(100, 100, 800, 600)
                self.__errorDialog.exec_()
                return

            while len(self.shaders) <= i:
                self.shaders.append(0)
            self.shaders[i] = program

            # 3D texture dirties, let's reset it's buffers too
            if self.passes[i].is3d and self.colorBuffers:
                for j, buffer in enumerate(self.colorBuffers[i]):
                    if isinstance(buffer, Texture3D):
                        self.colorBuffers[i][j] = buffer.original
                        self.__passDirtyState[i] = True

        self.__passDirtyState = [True] * len(self.passes)
        self.__errorDialog.close()

    def setCameraData(self, data):
        self.__cameraData = data

    def cameraData(self):
        return self.__cameraData

    def readCameraData(self):
        if self.__cameraData is None:
            userFile = FilePath(currentProjectFilePath() + '.user')
            xCamera = None
            if userFile.exists():
                xRoot = parseXMLWithIncludes(userFile)
                for xSub in xRoot:
                    if xSub.attrib['name'] == self.__filePath.name():
                        xCamera = xSub
                        break
            if xCamera is None:  # legacy support
                xCamera = parseXMLWithIncludes(self.__filePath)
            self.__cameraData = CameraTransform(*[float(x) for x in xCamera.attrib['camera'].split(',')])
        return self.__cameraData

    def setSize(self, w, h):
        if w == self.__w and h == self.__h:
            return
        self.__w = w
        self.__h = h

        # compose buffer metadata
        numBuffers = -1
        bufferData = OrderedDict()
        for passData in self.passes:
            if passData.targetBufferId not in bufferData:
                bufferData[passData.targetBufferId] = passData.numOutputBuffers, passData.downSampleFactor, passData.resolution, passData.tile
            else:
                numOutputBuffers, downSampleFactor, resolution, tile = bufferData[passData.targetBufferId]

                numOutputBuffers = max(numOutputBuffers, passData.numOutputBuffers)

                if passData.downSampleFactor is not None:
                    if downSampleFactor is not None:
                        assert passData.downSampleFactor == downSampleFactor
                    else:
                        downSampleFactor = passData.downSampleFactor

                if passData.resolution is not None:
                    if downSampleFactor is not None:
                        assert passData.resolution == resolution
                    else:
                        resolution = passData.resolution

                bufferData[passData.targetBufferId] = numOutputBuffers, downSampleFactor, resolution, tile

            numBuffers = max(passData.targetBufferId, numBuffers)
        numBuffers += 2
        bufferData[numBuffers - 1] = 1, 1, None, False

        self.frameBuffers = []
        self.colorBuffers = []
        for value in bufferData.values():
            if value[2] is not None:
                w, h = value[2]
            elif value[1] is not None:
                w, h = self.__w / value[1], self.__h / value[1]
            else:
                w, h = self.__w, self.__h

            self.frameBuffers.append(FrameBuffer(w, h))
            self.frameBuffers[-1].initDepth(Texture(Texture.FLOAT_DEPTH, w, h))
            self.colorBuffers.append([])
            for j in range(value[0]):
                self.colorBuffers[-1].append(Texture(Texture.RGBA32F, w, h, tile=value[3]))
                self.frameBuffers[-1].addTexture(self.colorBuffers[-1][-1])

        self.__passDirtyState = [True] * len(self.passes)

    def _bindInputs(self, passId, additionalTextureUniforms=None):
        j2d = 0
        j3d = 0

        j = 0

        # pull all textures in advance to avoid custom mip map shaders overriding the currently set up inputs
        program = glGetIntegerv(GL_CURRENT_PROGRAM)
        for j, inpt in enumerate(self.passes[passId].inputBufferIds):
            if isinstance(inpt, str):
                TexturePool.fetchAndUse(inpt)
        if additionalTextureUniforms:
            for name in additionalTextureUniforms:
                TexturePool.fetchAndUse(additionalTextureUniforms[name])
        glUseProgram(program)  # restore program

        for j, inpt in enumerate(self.passes[passId].inputBufferIds):
            glActiveTexture(GL_TEXTURE0 + j)

            if isinstance(inpt, str):
                # input is texture file name
                TexturePool.fetchAndUse(inpt)
                glUniform1i(glGetUniformLocation(self.shaders[passId], 'uImages[%s]' % j2d), j)
                j2d += 1
                continue

            frameBufferId, colorBufferId = inpt
            try:
                inputBuffer = self.colorBuffers[frameBufferId][colorBufferId]
            except IndexError as e:
                raise IndexError('Template for current scene has inputs fetching from non-existant buffers.')
            inputBuffer.use()
            if isinstance(inputBuffer, Texture3D):
                glUniform1i(glGetUniformLocation(self.shaders[passId], 'uImages3D[%s]' % j3d), j)
                j3d += 1
            else:
                glUniform1i(glGetUniformLocation(self.shaders[passId], 'uImages[%s]' % j2d), j)
                j2d += 1

        if additionalTextureUniforms:
            for name in additionalTextureUniforms:
                j += 1
                glActiveTexture(GL_TEXTURE0 + j)
                TexturePool.fetchAndUse(additionalTextureUniforms[name])
                glUniform1i(glGetUniformLocation(self.shaders[passId], name), j)

        return j + 1

    def _unbindInputs(self, maxActiveInputs):
        for j in range(maxActiveInputs):
            glActiveTexture(GL_TEXTURE0 + j)
            glBindTexture(GL_TEXTURE_2D, 0)

    def drawToScreen(self, seconds, beats, uniforms, viewport, additionalTextureUniforms=None):
        if not self.shaders:
            # compiler errors
            return

        # clear all frame buffers from Z before draw
        glEnable(GL_DEPTH_TEST)
        toClear = []
        for i, passData in enumerate(self.passes):
            if not self.__passDirtyState[i]:
                continue
            toClear.append(passData.targetBufferId)
        for i in sorted(list(set(toClear))):
            self.frameBuffers[i].use()
            glClear(GL_DEPTH_BUFFER_BIT)

        maxActiveInputs = max(1, self.draw(seconds, beats, uniforms, additionalTextureUniforms=additionalTextureUniforms))
        self._unbindInputs(maxActiveInputs)

        glDisable(GL_DEPTH_TEST)
        if self._debugPassId is None:
            Scene.drawColorBufferToScreen(self.colorBuffers[self.passes[-1].targetBufferId][0], viewport)
        else:
            a = self.colorBuffers[self.passes[self._debugPassId[0]].targetBufferId]
            Scene.drawColorBufferToScreen(a[max(0, min(self._debugPassId[1], len(a) - 1))], viewport)
        glEnable(GL_DEPTH_TEST)

    def draw(self, seconds, beats, uniforms, additionalTextureUniforms=None):
        if not self.shaders:
            # compiler errors
            return

        isProfiling = Profiler.instance and Profiler.instance.isVisible() and Profiler.instance.isProfiling() and self._debugPassId is None
        if isProfiling:
            self.profileLog = []
            glFinish()
            startT = time.clock()
        else:
            startT = time.clock()

        maxActiveInputs = 0
        for i, passData in enumerate(self.passes):
            if not self.__passDirtyState[i]:
                continue

            if self.passes[i].is3d:
                bail = False
                for buffer in self.colorBuffers[passData.targetBufferId]:
                    if isinstance(buffer, Texture3D):
                        # can't rebake
                        bail = True
                        break
                if bail:
                    continue

            self.__passDirtyState[i] = self.passes[i].realtime  # dirty again only if realtime

            uniforms['uSeconds'] = seconds
            uniforms['uBeats'] = beats
            uniforms['uResolution'] = self.frameBuffers[passData.targetBufferId].width(), \
                                      self.frameBuffers[passData.targetBufferId].height()

            if i >= len(self.shaders) or self.shaders[i] == 0:
                self._rebuild(None, index=i)

            # make sure we don't take into account previous GL calls when measuring time
            if isProfiling:
                glFinish()
                beforeT = time.clock()

            self.frameBuffers[passData.targetBufferId].use()

            glUseProgram(self.shaders[i])

            activeInputs = self._bindInputs(i, additionalTextureUniforms)

            fn = (glUniform1f, glUniform2f, glUniform3f, glUniform4f)
            for name in uniforms:
                if isinstance(uniforms[name], (int, long)):
                    glActiveTexture(GL_TEXTURE0 + activeInputs)
                    glBindTexture(GL_TEXTURE_2D, uniforms[name])
                    glUniform1i(glGetUniformLocation(self.shaders[i], name), activeInputs)
                    activeInputs += 1
                elif isinstance(uniforms[name], float):
                    fn[0](glGetUniformLocation(self.shaders[i], name), uniforms[name])
                elif len(uniforms[name]) == 9:
                    glUniformMatrix3fv(glGetUniformLocation(self.shaders[i], name), 1, False, (ctypes.c_float * 9)(*uniforms[name]))
                elif len(uniforms[name]) == 16:
                    glUniformMatrix4fv(glGetUniformLocation(self.shaders[i], name), 1, False, (ctypes.c_float * 16)(*uniforms[name]))
                else:
                    fn[len(uniforms[name]) - 1](glGetUniformLocation(self.shaders[i], name), *uniforms[name])

            for name in passData.uniforms:
                if isinstance(passData.uniforms[name], float):
                    fn[0](glGetUniformLocation(self.shaders[i], name), passData.uniforms[name])
                else:
                    fn[len(passData.uniforms[name]) - 1](glGetUniformLocation(self.shaders[i], name), *passData.uniforms[name])

            maxActiveInputs = max(maxActiveInputs, activeInputs)

            if self.passes[i].drawCommand is not None:
                exec self.passes[i].drawCommand
            else:
                FullScreenRectSingleton.instance().draw()

            # duct tape the 2D color buffer(s) into 3D color buffer(s)
            if self.passes[i].is3d:
                buffers = self.colorBuffers[passData.targetBufferId]
                for j, buffer in enumerate(buffers):
                    buffer.use()
                    data = glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_FLOAT)
                    FrameBuffer.clear()
                    buffers[j] = Texture3D(Texture.RGBA32F, buffer.height(), True, data)
                    buffers[j].original = buffer

            # enable mip mapping on static textures
            if not self.passes[i].realtime:
                # after rendering grab all render targets & enable mip maps, then generate them
                for buffer in self.colorBuffers[passData.targetBufferId]:
                    buffer.use()
                    mode = GL_TEXTURE_3D if isinstance(buffer, Texture3D) else GL_TEXTURE_2D
                    glTexParameteri(mode,
                                    GL_TEXTURE_MIN_FILTER,
                                    GL_LINEAR_MIPMAP_LINEAR)
                    glTexParameteri(mode,
                                    GL_TEXTURE_MAG_FILTER,
                                    GL_LINEAR)

                    # requires openGL 4.6?
                    glTexParameterf(mode, texture_filter_anisotropic.GL_TEXTURE_MAX_ANISOTROPY_EXT, 16.0)

                    glGenerateMipmap(mode)

            # make sure all graphics calls are finished processing in GL land before we measure time
            if isProfiling:
                glFinish()
                afterT = time.clock()
                self.profileLog.append((passData.name or str(i), afterT - beforeT))

            if self._debugPassId is not None and i == self._debugPassId[0]:
                # debug mode, we want to view this pass on the screen, avoid overwriting it's buffers with future passes
                break

        if isProfiling:
            glFinish()
        # inform the profiler a new result is ready
        endT = time.clock()
        self.profileInfoChanged.emit(endT - startT)

        return maxActiveInputs
