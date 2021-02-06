from pycompat import *
import os
import sys
import struct

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from build.codeoptimize import optimizeText
from fileutil import FilePath
from util import parseXMLWithIncludes, SCENE_EXT, currentScenesDirectory

gAnimEntriesMax = 0.0


def nextSubList(mainList, subList, offset=0):
    n = len(subList)
    for i in range(offset, len(mainList) - n + 1):
        if mainList[i:i + n] == subList:
            return i
    return -1


def rMatch(mainList, subList):
    # returns N where the last N items of mainList match the first N items of subList
    n = len(subList)
    n1 = len(mainList)
    if n1 >= n and mainList[-n:] == subList:
        return n
    if n1 < n:
        if mainList == subList[:n1]:
            return n1
        return 0
    for i in range(n - 1, -1, -1):
        if mainList[-i:] == subList[:i]:
            return i
    return 0


class TextPool(object):
    def __init__(self):
        self.data = []
        self.keys = []

    def addFile(self, filePath):
        assert isinstance(filePath, FilePath)
        text = optimizeText(filePath.content())
        return self.addString(text.replace('\n', '\\n\\\n') + '\\n\\0')

    def addString(self, value):
        key = value.lower()
        try:
            return self.keys.index(key)
        except ValueError:
            self.data.append(value)
            self.keys.append(key)
            return len(self.data) - 1

    def serialize(self):
        for i, v in enumerate(self.data):
            self.data[i] = v
        yield 'const char* gTextPool[] {"%s"};\n' % '",\n"'.join(v for v in self.data)


class ShaderPool(object):
    def __init__(self):
        self.data = []
        self.offsets = []

    def _findOrAddStitches(self, stitches):
        # pattern of stitches already exist ?
        idx = nextSubList(self.data, stitches)
        if idx != -1:
            return idx
        # match part of stitches at tail ?
        idx = rMatch(self.data, stitches)
        out = len(self.data) - idx
        if idx != len(stitches):
            self.data.extend(stitches[idx:])
        return out

    def fromStitches(self, stitches):
        assert isinstance(stitches, list)
        idx = self._findOrAddStitches(stitches)
        key = (idx, len(stitches))
        if key in self.offsets:
            return self.offsets.index(key)
        self.offsets.append(key)
        return len(self.offsets) - 1

    def serialize(self):
        yield 'GLuint gPrograms[%s];\n' % len(self.offsets)
        flat = []
        for offset in self.offsets:
            flat += [offset[1], offset[0]]
        cursor = ints.addInts(flat)
        yield '__forceinline void TickLoader(int, int);\n'
        yield '__forceinline void initPrograms(int width, int height)\n{\n'
        yield '\tint i = 0;\n'
        yield '\tconst char* gShaderStitchOrder[] = {gTextPool[%s]};\n' % '], gTextPool['.join(str(x) for x in self.data)
        yield '\tdo\n\t{\n'
        yield """\t\t#ifdef _DEBUG\n\t\tOutputDebugString("\\n\\n\\n--------------------------------\\n\\n\\n");\n\t\tfor (int j = 0; j < gIntData[%s + i * 2]; ++j)\n\t\t{\n\t\t\tOutputDebugString(gShaderStitchOrder[gIntData[%s + i * 2] + j]);\n\t\t}\n\t\tOutputDebugString("\\n\\n\\n--------------------------------\\n\\n\\n");\n\t\t#endif\n""" % (
            cursor, cursor + 1)
        yield '\t\tgPrograms[i] = glCreateShaderProgramv(GL_FRAGMENT_SHADER, gIntData[%s + i * 2], &gShaderStitchOrder[gIntData[%s + i * 2]]);\n' % (cursor, cursor + 1)
        yield '\t\tTickLoader(width, height);\n'
        yield '\t}\n\twhile(++i < %s);\n' % len(self.offsets)
        yield '}\n'


class FrameBufferPool(object):
    BLOCK_SIZE = 6

    def __init__(self):
        self.data = []
        self.keys = []

    def hasData(self):
        return self.data

    def add(self, index, numOutputs, width, height, factor, static, is3d):
        if index in self.keys:
            idx = self.keys.index(index)
            assert self.data[idx] == (numOutputs, width, height, factor, static, is3d), '%s != %s' % (self.data[idx], (numOutputs, width, height, factor, static, is3d))
            return idx
        else:
            self.data.append((numOutputs, width, height, factor, static, is3d))
            self.keys.append(index)
        return len(self.keys) - 1

    def textureId(self, frameBuffer, localOutput):
        frameBuffer = self.keys.index(frameBuffer)
        cursor = 0
        for i, data in enumerate(self.data):
            if i == frameBuffer:
                return cursor + localOutput, self.data[frameBuffer][-1]
            cursor += data[0]

    def serialize(self):
        allData = []
        totalTextures = 0
        for data in self.data:
            numOutputs, width, height, factor, static, is3d = data
            if width <= 0 or height <= 0:
                data = (numOutputs, 0, 0, factor, static, is3d)
            else:
                data = (numOutputs, width, height, factor, static, is3d)
            allData += [int(x) for x in data]
            totalTextures += int(data[0])

        if allData:
            global gFrameBufferData
            gFrameBufferData = ints.addInts(allData)
            yield 'GLuint gTextures[%s];\n' % totalTextures
            yield 'GLuint gFrameBuffers[%s];\n' % (len(self.data) + 1)
            yield 'GLuint* gFrameBufferColorBuffers[%s];\n' % (len(self.data) + 1)
        yield '\n\n__forceinline void widthHeight(int i, int width, int height, int& w, int& h)\n{\n'
        if allData:
            yield '\tw = gIntData[i * %s + %s];\n' % (FrameBufferPool.BLOCK_SIZE, gFrameBufferData + 1)
            yield '\th = gIntData[i * %s + %s];\n' % (FrameBufferPool.BLOCK_SIZE, gFrameBufferData + 2)
            yield '\tif(w == 0)\n\t\t\t{\n'
            yield '\t\tw = width;\n'
            yield '\t\th = height;\n'
            yield '\t}\n'
            yield '\tw /= gIntData[i * %s + %s];\n' % (FrameBufferPool.BLOCK_SIZE, gFrameBufferData + 3)
            yield '\th /= gIntData[i * %s + %s];\n' % (FrameBufferPool.BLOCK_SIZE, gFrameBufferData + 3)
        yield '}\n'
        yield '\n\n__forceinline void initFrameBuffers(int width, int height)\n{\n'
        if allData:
            yield '\tgFrameBuffers[0] = 0;\n'
            yield '\tglGenFramebuffers(%s, &gFrameBuffers[1]);\n' % len(self.data)
            yield '\tglGenTextures(%s, gTextures);\n' % totalTextures
            yield '\tint textureCursor = 0;\n'
            yield '\tint i = 0;\n'
            yield '\tdo\n\t{\n'
            yield '\t\tglBindFramebuffer(GL_FRAMEBUFFER, gFrameBuffers[i + 1]);\n'
            yield '\t\tint j = 0;\n'
            yield '\t\tgFrameBufferColorBuffers[i] = &gTextures[textureCursor];\n'
            yield '\t\tdo\n\t\t{\n'
            yield '\t\t\tglBindTexture(GL_TEXTURE_2D, gTextures[textureCursor]);\n'
            yield '\t\t\tint w, h;\n'
            yield '\t\t\twidthHeight(i, width, height, w, h);\n'
            yield '\t\t\tglTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA32F, w, h, 0, GL_RGBA, GL_FLOAT, NULL);\n'
            yield '\t\t\tglTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);\n'
            yield '\t\t\tglTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);\n'
            yield '\t\t\tif(gIntData[i * %s + %s] == 0)\n\t\t\t{\n' % (FrameBufferPool.BLOCK_SIZE, gFrameBufferData + 4)
            yield '\t\t\t\tglTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP);\n'
            yield '\t\t\t\tglTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP);\n'
            yield '\t\t\t}\n'
            yield '\t\t\tglFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0 + j, GL_TEXTURE_2D, gTextures[textureCursor++], 0);\n'
            yield '\t\t}\n\t\twhile(++j < gIntData[i * %s + %s]);\n' % (FrameBufferPool.BLOCK_SIZE, gFrameBufferData)
            yield '\t}\n\twhile(++i < %s);\n' % len(self.data)
        yield '}\n'


class PassPool(object):
    def __init__(self):
        self.data = []
        self.data2 = []

    def add(self, programId, buffer, inputs, uniforms):
        v = (programId, buffer + 1, inputs, uniforms)
        try:
            idx = self.data.index(v)
            return idx
        except ValueError:
            n = len(self.data)
            self.data.append(v)
            return n

    def serialize(self):
        yield '\n\n__forceinline void applyUniform(int dataSize, GLint uniformLocation, const float* dataHandle)\n{\n'
        yield '\tswitch(dataSize)\n\t{\n'
        yield '\tcase 1:\n'
        yield '\t\tglUniform1fv(uniformLocation, 1, dataHandle);\n'
        yield '\t\tbreak;\n'
        yield '\tcase 2:\n'
        yield '\t\tglUniform2fv(uniformLocation, 1, dataHandle);\n'
        yield '\t\tbreak;\n'
        yield '\tcase 3:\n'
        yield '\t\tglUniform3fv(uniformLocation, 1, dataHandle);\n'
        yield '\t\tbreak;\n'
        yield '\tdefault:\n'
        yield '\t\tglUniform4fv(uniformLocation, 1, dataHandle);\n'
        yield '\t\tbreak;\n'
        yield '\t}\n'
        yield '}\n'
        yield '\n\n#include <stdio.h>\n'
        yield 'char gFormatBuffer[128];\n'
        yield 'const GLenum gBufferBindings[] = { GL_COLOR_ATTACHMENT0 , GL_COLOR_ATTACHMENT0 + 1, GL_COLOR_ATTACHMENT0 + 2, GL_COLOR_ATTACHMENT0 + 3, GL_COLOR_ATTACHMENT0 + 4 , GL_COLOR_ATTACHMENT0 + 5, GL_COLOR_ATTACHMENT0 + 6, GL_COLOR_ATTACHMENT0 + 7};\n'
        flat = []
        for x in self.data:
            flat += [x[0], x[1]]
        global gPassProgramsAndTargets
        gPassProgramsAndTargets = ints.addInts(flat)
        maxConstUniforms = max(len(x[3]) for x in self.data)
        maxInputs = max(len(x[2]) for x in self.data)
        constUniformData = []
        inputData = []
        for entry in self.data:  # foreach pass
            constUniformData.append(len(entry[3]))  # track num uniforms in this pass
            for uniformStringId in entry[3]:  # register uniform name, data size (determines what function to call), index in the float array where the data is stored
                constUniformData.append(uniformStringId)
                uniformSize, floatOffset = entry[3][uniformStringId]
                constUniformData.append(floatOffset)
                constUniformData.append(uniformSize)
            constUniformData += [0] * (3 * (maxConstUniforms - len(entry[3])))
            inputData.append(len(entry[2]))
            for tex in entry[2]:
                inputData.extend(framebuffers.textureId(*tex))
            inputData += [0] * ((maxInputs - len(entry[2])) * 2)
        if constUniformData:
            global gPassConstUniforms
            gPassConstUniforms = ints.addInts(constUniformData)
        global gPassInputs
        gPassInputs = ints.addInts(inputData)
        yield '__forceinline bool bindPass(int passIndex, float seconds, float beats, int width, int height, bool isPrecalcStep)\n{\n'
        global gFrameBufferData
        if framebuffers.hasData():
            yield '\tint frameBufferId = gIntData[passIndex * 2 + %s] - 1;\n' % (gPassProgramsAndTargets + 1)
            yield '\tif(frameBufferId < 0)\n\t{\n'
            yield '\t\tif(isPrecalcStep)\n\t\t{\n'
            yield '\t\t\treturn false;\n'
            yield '\t\t}\n'
            yield '\t}\n'
            yield '\telse if (!isPrecalcStep && gIntData[frameBufferId * %s + %s])\n\t{\n' % (FrameBufferPool.BLOCK_SIZE, gFrameBufferData + 4)
            yield '\t\treturn false;\n'
            yield '\t}\n'

        yield '\tint w = width;\n'
        yield '\tint h = height;\n'
        yield '\tGLuint shader = gPrograms[gIntData[passIndex * 2 + %s]];\n' % gPassProgramsAndTargets
        yield '\tglUseProgram(shader);\n'
        if framebuffers.hasData():
            yield '\tglBindFramebuffer(GL_FRAMEBUFFER, gFrameBuffers[frameBufferId + 1]);\n'
            yield '\tif(frameBufferId >= 0)\n\t{\n'
            yield '\t\tglDrawBuffers(gIntData[frameBufferId * %s + %s], gBufferBindings);\n' % (FrameBufferPool.BLOCK_SIZE, gFrameBufferData)
            yield '\t\twidthHeight(frameBufferId, width, height, w, h);\n'
            yield '\t}\n'
        yield '\tglViewport(0, 0, w, h);\n'
        yield '\tglUniform2f(glGetUniformLocation(shader, "uResolution"), (float)w, (float)h);\n'
        yield '\tglUniform1f(glGetUniformLocation(shader, "uSeconds"), seconds);\n'
        yield '\tglUniform1f(glGetUniformLocation(shader, "uBeats"), beats);\n'

        if framebuffers.hasData():
            yield '#ifdef SUPPORT_3D_TEXTURE\n\tint j3d = -1, j2d = -1;\n#endif\n\tchar formatStr[] = "uImages[0]\\0\\0\\0";\n\tfor(int j = 0 ; j < gIntData[passIndex * %s + %s]; ++j)\n\t{\n' % (maxInputs * 2 + 1, gPassInputs)
            yield '\t\tglActiveTexture(GL_TEXTURE0 + j);\n'
            yield '\t\tint b, o = 7;\n'
            yield '#ifdef SUPPORT_3D_TEXTURE\n'
            yield '\t\tint mode = gIntData[passIndex * %s + %s + j * 2];\n' % (maxInputs * 2 + 1, gPassInputs + 2)
            yield '\t\tglBindTexture(mode ? GL_TEXTURE_3D : GL_TEXTURE_2D, gTextures[gIntData[passIndex * %s + %s + j * 2]]);\n' % (maxInputs * 2 + 1, gPassInputs + 1)
            yield """\t\tif (mode)\n\t\t{\n\t\t\tb = j3d++;\n\t\t\tformatStr[o++] = '3';\n\t\t\tformatStr[o++] = 'D';\n\t\t}\n\t\telse\n\t\t\tb = j2d++;\n#else\n"""
            yield '\t\tglBindTexture(GL_TEXTURE_2D, gTextures[gIntData[passIndex * %s + %s + j * 2]]);\n' % (maxInputs * 2 + 1, gPassInputs + 1)
            yield """\t\tb = j;\n#endif\n\t\tformatStr[o++] = '[';\n\t\tif (j >= 10)\n\t\t\tformatStr[o++] = '0' + (b / 10);\n\t\tformatStr[o++] = '0' + (b % 10);\n\t\tformatStr[o++] = ']';\n\t\tformatStr[o] = '\\0';\n\t\tglUniform1i(glGetUniformLocation(shader, formatStr), j);\n\t}"""

        if constUniformData:
            yield '\tfor(int j = 0; j < gIntData[passIndex * %s + %s]; ++j)\n\t{\n' % (3 * maxConstUniforms + 1, gPassConstUniforms)
            yield '\t\tGLint loc = glGetUniformLocation(shader, gTextPool[gIntData[passIndex * %s + %s + j * 3]]);\n' % (3 * maxConstUniforms + 1, gPassConstUniforms + 1)
            yield '\t\tconst float* ptr = &gFloatData[gIntData[passIndex * %s + %s + j * 3]];\n' % (3 * maxConstUniforms + 1, gPassConstUniforms + 2)
            yield '\t\tapplyUniform(gIntData[passIndex * %s + %s + j * 3], loc, ptr);\n' % (3 * maxConstUniforms + 1, gPassConstUniforms + 3)
            yield '\t}\n'
        yield '\treturn true;\n'
        yield '}\n'


def roundb(value, bits):
    # Truncation utility from: http://www.ctrl-alt-test.fr/?p=535
    if value == 'FLT_MAX':
        # cheat to work around constant used by stepped tangents
        return value
    if bits >= 32:
        return value
    bits = 32 - bits
    num = struct.unpack('i', struct.pack('f', value))[0]
    num = (num + (1 << (bits - 1))) & (-1 << bits)
    return struct.unpack('f', struct.pack('i', num))[0]


class FloatPool(ShaderPool):
    def addFloats(self, values, name=None):  # name may be used to selectively use roundb()
        # truncate floats
        values = [roundb(v, 32) for v in values]
        offset = self._findOrAddStitches(values)
        assert self.data[offset:offset + len(values)] == values
        return offset

    def serialize(self):
        data = [(str(x) + 'f' if x != 'FLT_MAX' else x) for x in self.data]
        yield 'const float gFloatData[] = {%s};\n' % ', '.join(data)


class IntPool(ShaderPool):
    def addInts(self, values):
        offset = self._findOrAddStitches(values)
        assert self.data[offset:offset + len(values)] == values
        return offset

    def serialize(self):
        yield 'const int gIntData[] = {%s};\n' % ', '.join(str(int(x)) for x in self.data)


text = TextPool()
shaders = ShaderPool()
framebuffers = FrameBufferPool()
passes = PassPool()
floats = FloatPool()
ints = IntPool()

_templates = {}


def Template(templatePath):
    assert isinstance(templatePath, FilePath)
    global _templates
    key = os.path.abspath(templatePath).lower()
    try:
        return _templates[key]
    except:
        xTemplate = parseXMLWithIncludes(templatePath)
        if _templates:
            raise RuntimeError('Found multiple templates in project, this is currently not supported by the player code.')
        _templates[key] = xTemplate
        return xTemplate


def run():
    shots = []
    scenes = []
    scenesDir = currentScenesDirectory()

    for scenePath in scenesDir.iter(join=True):
        if not scenePath.hasExt(SCENE_EXT):
            continue
        sceneDir = FilePath(scenePath.strip()).stripExt()
        xScene = parseXMLWithIncludes(scenePath)

        templatePath = scenesDir.join(scenesDir, xScene.attrib['template'])
        templateDir = templatePath.stripExt()
        xTemplate = Template(templatePath)

        scene = []

        for xPass in xTemplate:
            stitchIds = []
            uniforms = {}
            for xSection in xPass:
                baseDir = sceneDir
                if xSection.tag in ('global', 'shared'):
                    baseDir = templateDir
                shaderFile = baseDir.join(xSection.attrib['path']).abs()
                stitchIds.append(text.addFile(shaderFile))
                for xUniform in xSection:
                    name = xUniform.attrib['name']
                    values = [float(x.strip()) for x in xUniform.attrib['value'].split(',')]
                    uniforms[text.addString(name)] = len(values), floats.addFloats(values, name)

            programId = shaders.fromStitches(stitchIds)

            buffer = int(xPass.attrib.get('buffer', -1))
            outputs = int(xPass.attrib.get('outputs', 1))
            size = int(xPass.attrib.get('size', 0))
            width = int(xPass.attrib.get('width', size))
            height = int(xPass.attrib.get('height', size))
            factor = int(xPass.attrib.get('factor', 1))
            static = int(xPass.attrib.get('static', 0))
            is3d = int(xPass.attrib.get('is3d', 0))
            if buffer != -1:
                buffer = framebuffers.add(buffer, outputs, width, height, factor, static, is3d)

            i = 0
            key = 'input%s' % i
            inputs = []
            while key in xPass.attrib:
                v = xPass.attrib[key]
                if '.' in v:
                    a, b = v.split('.')
                else:
                    a, b = v, 0
                inputs.append((int(a), int(b)))
                i += 1
                key = 'input%s' % i

            scene.append(passes.add(programId, buffer, inputs, uniforms))

        sceneIndex = len(scenes)
        scenes.append(len(scene))
        scenes += scene

        for xShot in xScene:
            if xShot.attrib.get('enabled', 'True') == 'False':
                continue
            animations = {}
            for xChannel in xShot:
                uname = xChannel.attrib['name']
                n = uname
                x = 0
                if '.' in uname:
                    n, x = uname.rsplit('.', 1)
                    x = 'xyzw'.index(x)
                n = text.addString(n)
                if n not in animations:
                    animations[n] = []
                if not xChannel.text:
                    keyframes = []
                else:
                    keyframes = []
                    for i, v in enumerate(float(v.strip()) for v in xChannel.text.split(',')):
                        j = i % 8
                        if j == 0 or j == 4 or j > 5:
                            continue
                        if j == 5:  # out tangent y
                            if v == float('inf'):  # stepped tangents are implemented as out tangentY = positive infinity
                                v = 'FLT_MAX'
                        keyframes.append(v)
                    assert len(keyframes) / 4.0 == int(len(keyframes) / 4), len(keyframes)
                while len(animations[n]) <= x:
                    animations[n].append(None)
                assert animations[n][x] is None
                animations[n][x] = floats.addFloats(keyframes), len(keyframes)

            for channelStack in animations.values():
                # TODO we can not / do not check if the channelStack length matches the uniform dimensions inside the shader (e.g. are we sure we're not gonna call glUniform2f for a vec3?)
                assert None not in channelStack, 'Animation provided for multiple channels but there is one missing (Y if a vec3 or also Z if a vec4).'

            shots.append((float(xShot.attrib['start']), float(xShot.attrib['end']), sceneIndex, animations))

    # sort shots by start time
    def _serializeShots(shots):
        shots.sort(key=lambda x: x[0])
        shotTimesStart = floats.addFloats([x for shot in shots for x in (shot[0], shot[1])])
        yield '\n\n__forceinline int shotAtBeats(float beats, float& localBeats)\n{\n'
        if len(shots) == 1:
            yield '\tlocalBeats = beats - gFloatData[%s];\n' % shotTimesStart
            yield '\treturn 0;\n'
        else:
            yield '\tint shotTimeCursor = 0;\n'
            yield '\tdo\n\t{\n'
            yield '\t\tif(beats < gFloatData[shotTimeCursor * 2 + %s])\n\t\t{\n' % (shotTimesStart + 1)
            yield '\t\t\tlocalBeats = beats - gFloatData[shotTimeCursor * 2 + %s];\n' % shotTimesStart
            yield '\t\t\treturn shotTimeCursor;\n'
            yield '\t\t}\n'
            yield '\t}\n\twhile(++shotTimeCursor < %s);\n' % len(shots)
            yield '\treturn -1;\n'
        yield '}\n'

        global gShotScene
        gShotScene = ints.addInts([shot[2] for shot in shots])
        flatAnimationData = []
        animationDataPtrs = []
        for shot in shots:
            animationDataPtrs += [len(flatAnimationData), len(shot[3].keys())]
            global gAnimEntriesMax
            gAnimEntriesMax = max(gAnimEntriesMax, len(shot[3].keys()))
            for uniformStringId in shot[3]:
                animationData = shot[3][uniformStringId]
                flatAnimationData += [uniformStringId, len(animationData)]
                for pair in animationData:
                    flatAnimationData += pair
                flatAnimationData += [0] * (2 * (4 - len(animationData)))

        global gShotAnimationDataIds
        gShotAnimationDataIds = ints.addInts(animationDataPtrs)
        global gShotUniformData
        gShotUniformData = ints.addInts(flatAnimationData)

    def _serializeAll(scenes, shots):
        buffer = list(_serializeShots(shots))
        for serializable in (text, floats):
            for ln in serializable.serialize():
                yield ln
        buffer2 = []
        for serializable in (shaders, framebuffers, passes):
            buffer2 += list(serializable.serialize())
        global gScenePassIds
        gScenePassIds = ints.addInts(scenes)
        for ln in ints.serialize():
            yield ln
        for ln in buffer2:
            yield ln
        for ln in buffer:
            yield ln

    data = [''.join(_serializeAll(scenes, shots))]
    data.append("""\n\n__forceinline float evalCurve(const float* data, int numFloats, float beats)
{
\tif(numFloats == 4 || beats <= data[1]) // 1 key or evaluating before first frame
\t\treturn data[2];

\t// Find index of first key that has a bigger time than our current time
\t// if none, this will be the index of the last key.
\tint keyValueCount = numFloats;
\tint rightKeyIndex = 4;
\twhile (rightKeyIndex < keyValueCount - 4 && data[rightKeyIndex + 1] < beats)
\t\trightKeyIndex += 4;

\t// Clamp our sampling time to our range
\tfloat sampleTime = (beats > data[rightKeyIndex + 1]) ? data[rightKeyIndex + 1] : beats;

\t// Retrieve our spline points
\tfloat y0 = data[rightKeyIndex - 2];
\tfloat y1 = data[rightKeyIndex - 1]; 
\t// handle stepped tangents
\tif(y1 == FLT_MAX) return y0;
\tfloat y2 = data[rightKeyIndex];
\tfloat y3 = data[rightKeyIndex + 2];

\tfloat dy = y3 - y0;
\tfloat c0 = y1 + y2 - dy - dy;
\tfloat c1 = dy + dy + dy - y1 - y1 - y2;
\tfloat c2 = y1;
\tfloat c3 = y0;

\t// Determine factor
\tfloat dt = data[rightKeyIndex + 1] - data[rightKeyIndex - 3];
\tfloat t = (sampleTime - data[rightKeyIndex - 3]) / dt;

\treturn t * (t * (t * c0 + c1) + c2) + c3;
}

#define gAnimEntriesMax %s
#define gShotAnimationDataIds %s
#define gShotScene %s
#define gScenePassIds %s
#define gPassProgramsAndTargets %s
#define gShotUniformData %s
#define gFrameBufferData %s
#define gFrameBufferBlockSize %s
#define gProgramCount %s
""" % (gAnimEntriesMax, gShotAnimationDataIds, gShotScene, gScenePassIds, gPassProgramsAndTargets, gShotUniformData, gFrameBufferData, FrameBufferPool.BLOCK_SIZE, len(shaders.offsets)))

    dst = FilePath(__file__).abs().parent().parent().join('Player', 'generated.hpp')
    with dst.edit() as fh:
        fh.write(''.join(data))


if __name__ == '__main__':
    run()
