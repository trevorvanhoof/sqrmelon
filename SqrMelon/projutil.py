from qtutil import *
from xmlutil import parseXMLWithIncludes
from fileutil import FilePath

gSettings = QSettings('PB', 'Py64k')
PROJ_EXT = '.p64'
TEMPLATE_EXT = '.xml'
SCENE_EXT = '.xml'


def currentProjectFilePath():
    if not gSettings.contains('currentproject'):
        return None
    return FilePath(gSettings.value('currentproject'))


def setCurrentProjectFilePath(value):
    gSettings.setValue('currentproject', str(value))


def currentProjectDirectory():
    # AttributeError if no current project
    return currentProjectFilePath().parent()


def currentScenesDirectory():
    # AttributeError if no current project
    return currentProjectDirectory().join('Scenes')


def currentTemplatesDirectory():
    # AttributeError if no current project
    return currentProjectDirectory().join('Templates')


def templatePathFromScenePath(sceneFile):
    xScene = parseXMLWithIncludes(sceneFile)
    return sceneFile.join('..', xScene.attrib['template']).abs()


def iterSceneNames():
    scenes = currentScenesDirectory()
    if not scenes.exists():
        return []
    return [scene.name() for scene in scenes.iter() if scene.endswith(SCENE_EXT)]


def iterTemplateNames():
    for templatePath in currentTemplatesDirectory().iter(join=True):
        if not templatePath.hasExt(TEMPLATE_EXT):
            continue
        # ensure exists
        if not templatePath.isFile():
            continue
        if templatePath.name() == 'uniforms':
            continue
        yield templatePath.name()


def templateFolderFromName(name):
    return currentTemplatesDirectory().join(name)


def templateFileFromName(name):
    return currentTemplatesDirectory().join(name + TEMPLATE_EXT)


def _pathsFromTemplate(templatePath, tag, sceneDir=None):
    xTemplate = parseXMLWithIncludes(templatePath)
    if tag == 'section': assert sceneDir
    elif tag in ('shared', 'global'): assert not sceneDir
    baseDir = sceneDir or templatePath.ensureExt(None)
    for xPass in xTemplate:
        for xElement in xPass:
            if xElement.tag.lower() == tag:
                yield baseDir.join(xElement.attrib['path'])


def sectionPathsFromScene(sceneName):
    sceneDir = currentScenesDirectory().join(sceneName)
    sceneFile = sceneDir.ensureExt(SCENE_EXT)
    templatePath = templatePathFromScenePath(sceneFile)
    return _pathsFromTemplate(templatePath, 'section', sceneDir)


def sharedPathsFromTemplate(templateName):
    baseDir = currentTemplatesDirectory()
    templatePath = baseDir.join(templateName + TEMPLATE_EXT)
    return _pathsFromTemplate(templatePath, 'shared')
