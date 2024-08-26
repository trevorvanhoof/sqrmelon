from typing import Iterable, Optional

from fileutil import FilePath
from qt import *
from xmlutil import parseXMLWithIncludes

gSettings = QSettings('SqrMelon.ini', QSettings.Format.IniFormat)
PROJ_EXT = '.p64'
TEMPLATE_EXT = '.xml'
SCENE_EXT = '.xml'


def currentProjectFilePath() -> Optional[FilePath]:
    if not gSettings.contains('currentproject'):
        return None
    return FilePath(gSettings.value('currentproject')) # type: ignore


def setCurrentProjectFilePath(value: str) -> None:
    gSettings.setValue('currentproject', str(value))


def currentProjectDirectory() -> FilePath:
    # AttributeError if no current project
    projectPath = currentProjectFilePath()
    assert projectPath is not None
    return projectPath.parent()


def currentScenesDirectory() -> FilePath:
    # AttributeError if no current project
    return currentProjectDirectory().join('Scenes')


def currentTemplatesDirectory() -> FilePath:
    # AttributeError if no current project
    return currentProjectDirectory().join('Templates')


def templatePathFromScenePath(sceneFile: FilePath) -> FilePath:
    xScene = parseXMLWithIncludes(sceneFile)
    return sceneFile.join('..', xScene.attrib['template']).abs()


def iterSceneNames() -> Iterable[FilePath]:
    scenes = currentScenesDirectory()
    if not scenes.exists():
        return
    for scene in scenes.iter():
        if scene.endswith(SCENE_EXT):
            yield scene.name()


def iterTemplateNames() -> Iterable[FilePath]:
    for templatePath in currentTemplatesDirectory().iter(join=True):
        if not templatePath.hasExt(TEMPLATE_EXT):
            continue
        # ensure exists
        if not templatePath.isFile():
            continue
        if templatePath.name() == 'uniforms':
            continue
        yield templatePath.name()


def templateFolderFromName(name: str) -> FilePath:
    return currentTemplatesDirectory().join(name)


def templateFileFromName(name: str) -> FilePath:
    return currentTemplatesDirectory().join(name + TEMPLATE_EXT)


def _pathsFromTemplate(templatePath: FilePath, tag: str, sceneDir: Optional[FilePath] = None) -> Iterable[FilePath]:
    xTemplate = parseXMLWithIncludes(templatePath)
    if tag == 'section':
        assert sceneDir
    elif tag in ('shared', 'global'):
        assert not sceneDir
    baseDir = sceneDir or templatePath.ensureExt(None)
    for xPass in xTemplate:
        for xElement in xPass:
            if xElement.tag.lower() == tag:
                yield baseDir.join(xElement.attrib['path'])


def sectionPathsFromScene(sceneName: str) -> Iterable[FilePath]:
    sceneDir = currentScenesDirectory().join(sceneName)
    sceneFile = sceneDir.ensureExt(SCENE_EXT)
    templatePath = templatePathFromScenePath(sceneFile)
    return _pathsFromTemplate(templatePath, 'section', sceneDir)


def sharedPathsFromTemplate(templateName: str) -> Iterable[FilePath]:
    baseDir = currentTemplatesDirectory()
    templatePath = baseDir.join(templateName + TEMPLATE_EXT)
    return _pathsFromTemplate(templatePath, 'shared')
