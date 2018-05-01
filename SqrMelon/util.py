import os
from xml.etree import cElementTree
import colorsys
import xml.dom.minidom
import fileutil
from qtutil import *
import re

gSettings = QSettings('PB', 'Py64k')
PROJ_EXT = '.p64'
TEMPLATE_EXT = '.xml'
SCENE_EXT = '.xml'


def ParseXMLWithIncludes(xmlFilePath):
    with fileutil.read(xmlFilePath) as fh:
        text = fh.read()

    subs = []
    for result in re.finditer(r'<!--[ \t]*#[ \t]*include[ \t]+(.+)[ \t]*-->', text):
        inline = result.group(1).strip()
        with fileutil.read(os.path.join(os.path.dirname(xmlFilePath), inline)) as fh:
            inlineText = fh.read()
        subs.append((result.start(0), result.end(0), inlineText))

    for start, end, repl in reversed(subs):
        text = '{}{}{}'.format(text[:start], repl, text[end:])

    xRoot = cElementTree.fromstring(text)
    return xRoot


def ProjectFile():
    if not gSettings.contains('currentproject'):
        return None
    return gSettings.value('currentproject').replace('\\', '/')


def ProjectDir(sub=''):
    res = os.path.dirname(ProjectFile())
    if sub:
        return os.path.join(res, sub)
    return res


def ScenesPath(sub=''):
    projectDir = ProjectDir(sub)
    return os.path.join(projectDir, 'Scenes')


def TemplateForScene(sceneFile, sub=''):
    xScene = ParseXMLWithIncludes(sceneFile)
    return os.path.abspath(os.path.join(sceneFile, '..', xScene.attrib['template']))


def Scenes(sub=''):
    scenesPath = ScenesPath(sub)
    if not fileutil.exists(scenesPath):
        return []
    return [scene for scene in os.listdir(scenesPath) if scene.endswith(SCENE_EXT)]


def TemplatesPath(sub=''):
    return os.path.join(ProjectDir(sub), 'Templates')


def Templates(sub=''):
    templatesPath = TemplatesPath(sub)
    for sub in os.listdir(templatesPath):
        if not sub.endswith(TEMPLATE_EXT):
            continue
        if not os.path.isfile(os.path.join(templatesPath, sub).replace('\\', '/')):
            continue
        name = os.path.splitext(sub)[0]
        if fileutil.exists(os.path.join(templatesPath, name)):
            yield name


def TemplateFileFromName(name, sub=''):
    return os.path.join(TemplatesPath(sub), name + TEMPLATE_EXT)


def TemplateSourceFolderFromName(name, sub=''):
    return os.path.join(TemplatesPath(sub), name)


def toPrettyXml(root):
    root.text = None
    text = cElementTree.tostring(root)
    text = xml.dom.minidom.parseString(text).toprettyxml()
    text = text.replace('\r', '\n')
    return '\n'.join(line for line in text.split('\n') if line and line.strip())


_randomColorSeed = 0.0


def randomColor(seed=None):
    if seed is None:
        global _randomColorSeed
        _randomColorSeed = (_randomColorSeed + 0.7) % 1.0
        r, g, b = colorsys.hsv_to_rgb(_randomColorSeed, 0.4, 0.9)
    else:
        r, g, b = colorsys.hsv_to_rgb(seed, 0.4, 0.9)
    return r * 255, g * 255, b * 255


def sectionPathsFromScene(sceneName, sub=''):
    sceneDir = os.path.join(ScenesPath(sub), sceneName)
    sceneFile = sceneDir + SCENE_EXT
    templatePath = TemplateForScene(sceneFile, sub)
    xTemplate = ParseXMLWithIncludes(templatePath)
    for xPass in xTemplate:
        for xElement in xPass:
            if xElement.tag.lower() == 'section':
                yield os.path.join(sceneDir, xElement.attrib['path'])


def sharedPathsFromTemplate(templateName, sub=''):
    baseDir = TemplatesPath(sub)
    templatePath = os.path.join(baseDir, templateName) + TEMPLATE_EXT
    xTemplate = ParseXMLWithIncludes(templatePath)
    for xPass in xTemplate:
        for xElement in xPass:
            if xElement.tag.lower() == 'shared':
                yield os.path.join(baseDir, templateName, xElement.attrib['path'])
