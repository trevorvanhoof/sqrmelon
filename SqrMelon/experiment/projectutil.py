from qtutil import *


def settings():
    return QSettings('PB', 'SqrMelon')


def projectFolder():
    assert settings().contains('currentproject')
    return str(settings().value('currentproject'))


def templateFolder():
    return os.path.join(projectFolder(), 'Templates')
