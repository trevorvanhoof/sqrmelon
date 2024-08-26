# TODO: Add float truncation support.
# TODO: Every time I struct.pack some array of data I should actually define a (data)class that can serialize itself instead
#  so it is easier to see when our C++-side structs are mismatching.
import struct
from typing import Iterable, Mapping, TypeVar
from xml.etree import cElementTree

from PySide6.QtWidgets import QApplication

from animationgraph.curvedata import Key
from fileutil import FilePath
from projutil import currentProjectFilePath, currentScenesDirectory, iterSceneNames, SCENE_EXT, templatePathFromScenePath
from scene import deserializePasses, PassData
from shots import deserializeSceneShots, Shot

T = TypeVar("T")


def multiPack(*args):
    assert len(args) % 2 == 0
    blobs = []
    for key, value in zip(args[::2], args[1::2]):
        if hasattr(value, '__iter__'):
            if not value:
                assert key[0] == '0'
                continue
            blob = struct.pack(key, *value)
            cmp = struct.unpack(key, blob)
            if isinstance(value[0], float):
                # TODO: compare almost equal
                ...
            else:
                assert tuple(value) == cmp
        else:
            blob = struct.pack(key, value)
            cmp = struct.unpack(key, blob)[0]
            if isinstance(value, float):
                assert abs(cmp - value) < 1e-5
            else:
                assert value == cmp
        blobs.append(blob)
    return b''.join(blobs)


class BinaryPool:
    def __init__(self) -> None:
        self._sequence: bytes = b''

    def data(self) -> bytes:
        return self._sequence

    def ensureExists(self, value: bytes) -> int:
        try:
            index = self._sequence.index(value)
            assert self._sequence[index:index + len(value)] == value
            return index
        except ValueError:
            n = 1
            while n < len(value):
                if self._sequence.endswith(value[:-n]):
                    self._sequence += value[-n:]
                    index = len(self._sequence) - len(value)
                    assert self._sequence[index:index + len(value)] == value
                    return index
                n += 1
        self._sequence += value
        index = len(self._sequence) - len(value)
        assert self._sequence[index:index + len(value)] == value
        return index


def gatherEnabledShots(sceneNameIndexMap: Mapping[str, int]) -> list[Shot]:
    # Gather enabled shots across scense
    enabledShots: list[Shot] = []
    for sceneName in sceneNameIndexMap:
        for shot in deserializeSceneShots(sceneName):
            if not shot.enabled:
                continue
            enabledShots.append(shot)
    enabledShots.sort(key=lambda _shot: _shot.start)
    return enabledShots


def serializeShots(pool: BinaryPool, enabledShots: list[Shot]) -> tuple[int, list[str], int, int]:
    # Serialize shot times and validate the timeline
    timeCursor = 0.0
    shotEndTimes = []
    shotSceneNames = []
    maxAnimations = 0
    # For each shot we have: number of uniforms, that many uniform name indices, that many uniform sizes, and then all the curve indices in order
    shotInfo = []
    for shot in enabledShots:
        assert not shot.textures, f'Shot {shot.name} uses texture uniforms, this is an editor-only feature and not supported in the 64k runtime.'

        assert shot.start <= timeCursor, f'Gap in timeline found before: {shot.name}.'
        if shot.start != timeCursor:
            print(f'Warning: 2 shots animating at the same time at: {shot.name}. Accidentally left a shot enabled?')
        timeCursor = shot.end

        # Serialize the start time for all but the first shot
        shotEndTimes.append(shot.end)
        if shot == enabledShots[0] and shot.start != 0.0:
            print(f'Warning: first shot {shot.name} is assumed to start at 0.0, even though this is not the case.')

        # Bake preroll and speed before looking at the curves
        shot.bake()

        # Serialize shot curves
        # Track unique uniform names and what type they are (vec1,2,3,4)
        uniformNames: list[str] = []
        maxIndices: dict[str, int] = {}
        for name in shot.curves:
            if '.' in name:
                uniformName, element = name.rsplit('.', 1)
                index = 'xyzw'.index(element)
                maxIndices[uniformName] = max(maxIndices.get(uniformName, 0), index)
            else:
                uniformName = name
            if uniformName not in uniformNames:
                uniformNames.append(uniformName)

        # Register each unique uniform name and track the uniform names and curve per uniform
        uniformSizes = []
        uniformNameOffsets = []
        for uniformName in uniformNames:
            uniformSizes.append(maxIndices.get(uniformName, 0) + 1)
            nameIndex = pool.ensureExists(uniformName.encode('utf8') + b'\0')
            uniformNameOffsets.append(nameIndex)

        # stride, num uniforms, uniform name indices, uniform dimensions, uniform curve indices
        sizeOf = 2 + 1 + len(uniformNames) * 5 + sum(uniformSizes) * 4
        # TODO: Will there ever be 256 uniforms in a shot?
        blob = multiPack('HB', (sizeOf, len(uniformNames)), f'{len(uniformNameOffsets)}I', uniformNameOffsets, f'{len(uniformSizes)}B', uniformSizes)

        # store each curve and save its index into the blob for this shot
        for uniformName, elementCount in zip(uniformNames, uniformSizes):
            for element in range(elementCount):
                if elementCount == 1:
                    curveName = uniformName
                else:
                    curveName = uniformName + '.' + 'xyzw'[element]
                curve = shot.curves[curveName]

                keys = []
                for key in curve:
                    oty = float('inf') if key.tangentMode == Key.TANGENT_STEPPED else key.outTangent().y
                    keys += [key.inTangent().y, key.point().x, key.point().y, oty]

                # get num keys
                keysSize = len(keys) // 4
                # strip first in tangent and last out tangent as they are unused
                # TODO: is handling the edge case not larger?
                keys.pop(0)
                keys.pop(-1)

                # store the keys
                # TODO: Will there ever be 65536 keys in a curve?
                keysIndex = pool.ensureExists(multiPack('H', keysSize, f'{len(keys)}f', keys))
                blob += struct.pack('I', keysIndex)

        # Serialize all shot animation data as a single stream
        assert sizeOf == len(blob)
        shotInfo.append(blob)

        maxAnimations = max(maxAnimations, len(uniformNames))

        # Track the scene to use for this shot
        shotSceneNames.append(shot.sceneName)

    # TODO: Will there ever be 65536 shots in a demo?
    shotEndTimesIndex = pool.ensureExists(multiPack(f'{len(shotEndTimes)}f', shotEndTimes))
    shotAnimationInfoIndex = pool.ensureExists(b''.join(shotInfo))
    return shotEndTimesIndex, shotSceneNames, shotAnimationInfoIndex, maxAnimations


def iterUsedTemplatePasses(enabledShots: list[Shot]) -> Iterable[list[PassData]]:
    knownTemplatePaths = set()
    for shot in enabledShots:
        scenePath = currentScenesDirectory().join(shot.sceneName).ensureExt(SCENE_EXT)
        templatePath = templatePathFromScenePath(scenePath)
        if templatePath not in knownTemplatePaths:
            knownTemplatePaths.add(templatePath)
            yield deserializePasses(scenePath)


def readPassFBOInfo(passData: PassData) -> tuple[int, int, int, int]:
    w, h = 0, 0
    if passData.resolution:
        w, h = passData.resolution
    assert w < 65536, f'{passData.name} width value out of uint16 bounds. Not supported by current runtime.'
    assert h < 65536, f'{passData.name} height value out of uint16 bounds. Not supported by current runtime.'

    f = 1
    if passData.downSampleFactor:
        f = passData.downSampleFactor
    assert 0 < f < 256, f'{passData.name} factor value out of uint8 bounds. Not supported by current runtime.'

    assert passData.numOutputBuffers > 0, f'{passData.name} has 0 outputs to render into.'
    assert passData.numOutputBuffers < 32, f'{passData.name} outputs value out of uint5 (yes five) bounds. Not supported by current runtime.'

    packed = passData.numOutputBuffers | (passData.realtime << 7) | (passData.is3d << 6) | (passData.tile << 5)
    return w, h, f, packed


def serializeBuffers(pool: BinaryPool, enabledShots: list[Shot]) -> tuple[int, int, dict[int, int], list[int], int]:
    # For each used template, generate the framebuffer/colorbuffer construction info
    # and get a map of indices for: template frame buffer index -> real fbo index
    # and template color buffer index -> real cbo index
    fboConstructionInfo: list[tuple[int, int, int, int]] = []
    fboKeyToIndex: dict[int, int] = {}
    fboFirstCboIndex = [0]
    for passes in iterUsedTemplatePasses(enabledShots):
        for passData in passes:
            fboInfo = readPassFBOInfo(passData)
            if passData.targetBufferId in fboKeyToIndex:
                # Another pass already outputs to this buffer, verify that their requirements are identical.
                # TODO: Ignore numOutputBuffers difference and just use max?
                assert fboInfo == fboConstructionInfo[fboKeyToIndex[passData.targetBufferId]], f'A pass {passData.name} defines different framebuffer info from another pass targeting the same buffer. Note that this counts ACROSS TEMPLATES. Pass buffer indices do not have to start at 0 or be consecutive so you can transpose them if this is not intentional. It is recommended to reuse passes as much as possible, even if one has more outputs than the other it is OK to ignore the extra output targets.'
                continue
            if passData.targetBufferId == -1:
                continue
            fboKeyToIndex[passData.targetBufferId] = len(fboConstructionInfo)
            fboConstructionInfo.append(fboInfo)
            fboFirstCboIndex.append(fboFirstCboIndex[-1] + passData.numOutputBuffers)
    cboCount = fboFirstCboIndex.pop(-1)  # Value for "next" (non existant) pass is not necessary.

    # Dump the construction table, it'll fill arrays of GL fbo & cbo handles
    # that we can then index into using the values in these generated maps.
    fboBlockAddr = pool.ensureExists(b''.join(multiPack('HHBB', chunk) for chunk in fboConstructionInfo))
    fboCount = len(fboConstructionInfo)
    return fboBlockAddr, fboCount, fboKeyToIndex, fboFirstCboIndex, cboCount


def main() -> None:
    # We store all demo data as 1 big binary blob
    pool = BinaryPool()
    programs: dict[str, tuple[int, int]] = {}

    # Find all enabled shots and sort them by start time
    sceneNameIndexMap: Mapping[str, int] = {name: index for (index, name) in enumerate(iterSceneNames())}
    enabledShots = gatherEnabledShots(sceneNameIndexMap)

    # Add all shots to the demo
    shotEndTimesIndex, shotSceneNames, shotAnimationInfoIndex, maxAnimations = serializeShots(pool, enabledShots)

    # Add all required render buffers
    fboBlockAddr, fboCount, fboKeyToIndex, fboFirstCboIndex, cboCount = serializeBuffers(pool, enabledShots)

    # Add the shaders and uniforms for each scene
    sceneIds = []
    for sceneName in sceneNameIndexMap:
        # Every scene is just a list of passes to consume.
        scenePassIds = []
        for passData in deserializePasses(currentScenesDirectory().join(sceneName).ensureExt(SCENE_EXT)):
            if passData.uniforms:
                raise DeprecationWarning(f'Shader pass {passData.name} uses uniform XML elements inside the template. This used to be supported but was omitted in favor of using small shader stitches that simply declare constants with the right values instead.')
            stitchIds = []
            assert not passData.vertStitches, 'Vertex shaders are an experimental editor-only feature.'
            for shaderFilePath in passData.fragStitches:
                with shaderFilePath.readBinary() as fh:
                    # glShaderSource and glCreateShaderProgramv can take a list of strings
                    # and infer the lengths if the strings are null terminated (cheaper than storing the lengths).
                    # It will concatenate these strings without these nulls, so we also add a line break
                    # in case the strings can not be concatenated without whitespace (e.g. the second string starts with a #define).
                    txt = fh.read() + b'\n\0'
                stitchIds.append(pool.ensureExists(txt))
            # TODO: Will there ever be more than 256 stitches in a program?
            programKey = ','.join(str(stitchId) for stitchId in stitchIds)
            if programKey not in programs:
                stitchesAddr = pool.ensureExists(multiPack('B', len(stitchIds), f'{len(stitchIds)}I', stitchIds))
                programs[programKey] = len(programs), stitchesAddr
            programId = programs[programKey][0]
            if passData.targetBufferId == -1:
                fboId = 0b11111111
            else:
                fboId = fboKeyToIndex[passData.targetBufferId]
            cboIds = []
            for inputBufferId in passData.inputBufferIds:
                assert not isinstance(inputBufferId, FilePath), f'Shader pass {passData.name} specifies input texture by file path. This is an editor-only feature and not supported in the runtime.'
                cboId = fboFirstCboIndex[fboKeyToIndex[inputBufferId[0]]] + inputBufferId[1]
                cboIds.append(cboId)
            # Every scene is a list of passes, not all of them have sections, to avoid duplicating global passes
            # we add passes individually and then track the ids for the scene to render.
            # TODO: Will there ever be more than 256 inputs in a pass?
            scenePassIds.append(pool.ensureExists(multiPack('IBB', (programId, fboId, len(cboIds)), f'{len(cboIds)}B', cboIds)))
        # TODO: Will there ever be more than 256 passes?
        sceneIds.append(pool.ensureExists(multiPack('B', len(scenePassIds), f'{len(scenePassIds)}I', scenePassIds)))

    # List all the scene addresses for each shot to consume
    shotCount = len(shotSceneNames)
    shotSceneIds = [sceneIds[sceneNameIndexMap[sceneName]] for sceneName in shotSceneNames]
    shotSceneIdsIndex = pool.ensureExists(multiPack(f'{len(shotSceneIds)}I', shotSceneIds))

    # List all programs to compile
    # TODO: Will there ever be more than 65536 programs in a demo?
    programIds = [stitchesAddr for _, stitchesAddr in programs.values()]
    programsIndex = pool.ensureExists(multiPack(f'{len(programIds)}I', programIds))

    beatsPerSecond = cElementTree.fromstring(currentProjectFilePath().content()).attrib.get('TimerBPS', 2.0)

    # Globals to use in the framework
    outputPath = FilePath(__file__).abs().parent().parent().join('MelonPan', 'content', 'generated_eidolon.hpp')
    with outputPath.edit() as fh:
        fh.write('constexpr const unsigned char data[] = {')
        fh.write(', '.join(str(int(number)) for number in pool.data()))
        fh.write('};\n')
        assert 0 <= fboCount < 256
        fh.write(f'constexpr const unsigned int framebuffersInfoIndex = {fboBlockAddr};\n')
        fh.write(f'constexpr const unsigned char framebuffersCount = {fboCount};\n')
        fh.write(f'constexpr const unsigned int shotEndTimesIndex = {shotEndTimesIndex};\n')
        fh.write(f'constexpr const unsigned int shotSceneIdsIndex = {shotSceneIdsIndex};\n')
        fh.write(f'constexpr const unsigned int shotAnimationInfoIndex = {shotAnimationInfoIndex};\n')
        fh.write(f'constexpr const unsigned int programsIndex = {programsIndex};\n')
        fh.write(f'constexpr const unsigned char maxAnimations = {maxAnimations};\n')
        fh.write(f'constexpr const unsigned char cboCount = {cboCount};\n')
        fh.write(f'constexpr const unsigned char shotCount = {shotCount};\n')
        fh.write(f'constexpr const float beatsPerSecond = {beatsPerSecond}f;\n')
        fh.write(f'constexpr const unsigned short programCount = {len(programIds)};\n')

    print(f'Wrote: {currentProjectFilePath()}\nto: {outputPath}')


QApplication([])
main()
