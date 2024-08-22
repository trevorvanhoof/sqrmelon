# TODO: Add float truncation support.
# TODO: Every time I struct.pack some array of data I should actually define a (data)class that can serialize itself instead
#  so it is easier to see when our C++-side structs are mismatching.
import struct
from difflib import SequenceMatcher
from typing import Iterable, TypeVar

from animationgraph.curvedata import Key
from fileutil import FilePath
from projutil import currentScenesDirectory, iterSceneNames, SCENE_EXT, templatePathFromScenePath
from scene import deserializePasses, PassData
from shots import deserializeSceneShots, Shot

T = TypeVar("T")


class BinaryPool:
    def __init__(self) -> None:
        self._sequence: bytes = b''

    def ensureExists(self, value: bytes) -> int:
        blocks = SequenceMatcher(None, value, self._sequence).get_matching_blocks()
        for block in blocks:
            if block.size == len(value):
                return block.b
            if block.b + block.size == len(self._sequence):
                self._sequence += value[block.size:]
                return block.b
        b = len(self._sequence)
        self._sequence += value
        return b


def gatherEnabledShots(sceneNameIndexMap: dict[str, int]) -> list[Shot]:
    # Gather enabled shots across scense
    enabledShots: list[Shot] = []
    for sceneName in sceneNameIndexMap:
        for shot in deserializeSceneShots(sceneName):
            if not shot.enabled:
                continue
            enabledShots.append(shot)
    enabledShots.sort(key=lambda _shot: _shot.start)
    return enabledShots


def serializeShots(pool: BinaryPool, enabledShots: list[Shot]):
    # Serialize shot times and validate the timeline
    timeCursor = 0.0
    shotStartTimes = []  # omits the first time as it is always 0.0
    shotSceneNames = []
    shotInfo = []  # first value is nr of curves, next values are 3 ints of name index, keys index, num keys
    for shot in enabledShots:
        assert not shot.textures, f'Shot {shot.name} uses texture uniforms, this is an editor-only feature and not supported in the 64k runtime.'

        assert shot.start <= timeCursor, f'Gap in timeline found before: {shot.name}.'
        if shot.start != timeCursor:
            print(f'Warning: 2 shots animating at the same time at: {shot.name}. Accidentally left a shot enabled?')
        timeCursor = shot.end

        # Serialize the start time for all but the first shot
        if shot != enabledShots[0]:
            shotStartTimes.append(shot.start)
            if shot.start != 0.0:
                print(f'Warning: first shot {shot.name} is assumed to start at 0.0, even though this is not the case.')

        # Bake preroll and speed before looking at the curves
        shot.bake()

        # Serialize shot curves
        animations = []
        for name, curve in shot.curves.items():
            # store the name
            nameIndex = pool.ensureExists(name.encode('utf8') + b'\0')
            keys = []
            for key in curve:
                oty = float('inf') if key.tangentMode == Key.TANGENT_STEPPED else key.outTangent.y
                keys += [key.inTangent.y, key.point().x, key.point().y, oty]
            # get num keys
            keysSize = len(keys) // 4
            # strip first in tangent and last out tangent as they are unused
            # TODO: is handling the edge case not larger?
            keys.pop(0)
            keys.pop(-1)
            # store the keys
            # TODO: Will there ever be 65536 keys in a curve?
            keysIndex = pool.ensureExists(struct.pack(f'H{len(keys)}f', keysSize, *keys))
            animations.append(struct.pack('II', nameIndex, keysIndex))

        # Serialize the shot animation data as a single stream
        # TODO: Will there ever be 256 uniforms in a shot?
        shotInfo.append(struct.pack('B', len(animations)))
        shotInfo += animations

        # Serialize the scene to use for this shot
        shotSceneNames.append(shot.sceneName)

    shotStartTimesIndex = pool.ensureExists(struct.pack(f'{len(shotStartTimes)}f', *shotStartTimes))
    shotAnimationInfoIndex = pool.ensureExists(b''.join(shotInfo))
    return shotStartTimesIndex, shotSceneNames, shotAnimationInfoIndex


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
    assert passData.resolution[0] < 65536, f'{passData.name} width value out of uint16 bounds. Not supported by current runtime.'
    assert passData.resolution[1] < 65536, f'{passData.name} height value out of uint16 bounds. Not supported by current runtime.'

    f = 1
    if passData.downSampleFactor:
        f = passData.downSampleFactor
    assert 0 < passData.downSampleFactor < 256, f'{passData.name} factor value out of uint8 bounds. Not supported by current runtime.'

    assert passData.numOutputBuffers > 0, f'{passData.name} has 0 outputs to render into.'
    assert passData.numOutputBuffers < 64, f'{passData.name} outputs value out of uint6 (yes six) bounds. Not supported by current runtime.'

    packed = passData.numOutputBuffers | (passData.realtime << 7) | (passData.is3d << 6)
    return w, h, f, packed


def serializeBuffers(pool: BinaryPool, enabledShots: list[Shot]) -> tuple[int, int, dict[int, int], list[int]]:
    # For each used template, generate the framebuffer/colorbuffer construction info
    # and get a map of indices for: template frame buffer index -> real fbo index
    # and template color buffer index -> real cbo index
    fboConstructionInfo = []
    fboKeyToIndex = {}
    fboFirstCboIndex = [0]
    for passes in iterUsedTemplatePasses(enabledShots):
        for passData in passes:
            fboInfo = readPassFBOInfo(passData)
            if passData.targetBufferId in fboKeyToIndex:
                # Another pass already outputs to this buffer, verify that their requirements are identical.
                # TODO: Ignore numOutputBuffers difference and just use max?
                assert fboInfo == fboConstructionInfo[fboKeyToIndex[passData.targetBufferId]], f'A pass {passData.name} defines different framebuffer info from another pass targeting the same buffer. Note that this counts ACROSS TEMPLATES. Pass buffer indices do not have to start at 0 or be consecutive so you can transpose them if this is not intentional. It is recommended to reuse passes as much as possible, even if one has more outputs than the other it is OK to ignore the extra output targets.'
                continue
            fboKeyToIndex[passData.targetBufferId] = len(fboConstructionInfo)
            fboConstructionInfo.append(fboInfo)
            fboFirstCboIndex.append(fboFirstCboIndex[-1] + passData.numOutputBuffers)
    fboFirstCboIndex.pop(-1)  # Value for "next" (non existant) pass is not necessary.

    # Dump the construction table, it'll fill arrays of GL fbo & cbo handles
    # that we can then index into using the values in these generated maps.
    fboBlockAddr = pool.ensureExists(b''.join(struct.pack('HHBB', chunk) for chunk in fboConstructionInfo))
    fboCount = len(fboConstructionInfo)
    return fboBlockAddr, fboCount, fboKeyToIndex, fboFirstCboIndex


def main():
    # We store all demo data as 1 big binary blob
    pool = BinaryPool()

    # Find all enabled shots and sort them by start time
    sceneNameIndexMap = {name: index for (index, name) in enumerate(iterSceneNames())}
    enabledShots = gatherEnabledShots(sceneNameIndexMap)

    # Add all shots to the demo
    shotStartTimesIndex, shotSceneNames, shotAnimationInfoIndex = serializeShots(pool, enabledShots)

    # Add all required render buffers to the demo
    fboBlockAddr, fboCount, fboKeyToIndex, fboFirstCboIndex = serializeBuffers(pool, enabledShots)

    # Finally add the shaders and uniforms for each scene
    sceneIds = []
    for sceneName in sceneNameIndexMap:
        # Every scene is just a list of passes to consume.
        scenePassIds = []
        for passData in deserializePasses(currentScenesDirectory().join(sceneName).ensureExt(SCENE_EXT)):
            if passData.uniforms:
                raise DeprecationWarning(f'Shader pass {passData.name} uses uniform XML elements inside the template. This used to be supported but was omitted in favor of using small shader stitches that simply declare constants with the right values instead.')
            stitchIds = []
            for shaderFilePath in passData.vertStitches:
                txt = shaderFilePath.readBinary().read() + b'\0'
                stitchIds.append(pool.ensureExists(txt))
            for shaderFilePath in passData.fragStitches:
                txt = shaderFilePath.readBinary().read() + b'\0'
                stitchIds.append(pool.ensureExists(txt))
            # TODO: Will there ever be more than 256 stitches in a program?
            programId = pool.ensureExists(struct.pack(f'B{len(stitchIds)}I', len(stitchIds), *stitchIds))
            fboId = fboKeyToIndex[passData.targetBufferId]
            cboIds = []
            for inputBufferId in passData.inputBufferIds:
                assert not isinstance(inputBufferId, FilePath), f'Shader pass {passData.name} specifies input texture by file path. This is an editor-only feature and not supported in the runtime.'
                cboId = fboFirstCboIndex[fboKeyToIndex[inputBufferId[0]]] + inputBufferId[1]
                cboIds.append(cboId)
            # Every scene is a list of passes, not all of them have sections, to avoid duplicating global passes
            # we add passes individually and then track the ids for the scene to render.
            # TODO: Will there ever be more than 256 inputs in a pass?
            scenePassIds.append(pool.ensureExists(struct.pack(f'IIB{len(cboIds)}I', programId, fboId, len(cboIds), *cboIds)))
        # TODO: Will there ever be more than 256 passes?
        sceneIds.append(pool.ensureExists(struct.pack(f'B{len(scenePassIds)}I', len(scenePassIds), *scenePassIds)))

    # Finally list all the scene addresses for each shot to consume
    shotSceneIds = [sceneIds[sceneNameIndexMap[sceneName]] for sceneName in shotSceneNames]
    shotSceneIdsIndex = pool.ensureExists(struct.pack(f'{len(shotSceneIds)}I', *shotSceneIds))

    # Globals to use in the framework
    raise RuntimeError
    shotStartTimesIndex, shotSceneIdsIndex, shotAnimationInfoIndex, fboBlockAddr, fboCount



"""
vertStitches: list[FilePath]
fragStitches: list[FilePath]
uniforms: dict[str, list[float]]
inputBufferIds: list[Union[FilePath, tuple[int, int]]] = None
targetBufferId: int = -1
realtime: bool = True
resolution: Optional[tuple[int, int]] = None
tile: bool = False
downSampleFactor: Optional[int] = None
numOutputBuffers: int = 1
drawCommand: Optional[str] = None
is3d: bool = False
label: Optional[str] = None
"""
