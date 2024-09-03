import os
from fileutil import FilePath
from qt import QFont, QFontDatabase, QApplication, QPoint, QGuiApplication

__monospaceFont = None
__variableWidthFont = None

def _getPath(fontName: str) -> FilePath:
    path = FilePath(os.path.dirname(__file__)).join(fontName)
    if path.exists():
        return path
    raise Exception('Font file not found: "%s".'  % fontName)

def _loadFont(fontName: str) -> str:
#    fontSize = fontSize * QGuiApplication.instance().primaryScreen().devicePixelRatio()
    fontId = QFontDatabase.addApplicationFont(_getPath(fontName))
    if fontId == -1:
        print("Error loading font.")
        return None
    fontFamilies = QFontDatabase.applicationFontFamilies(fontId)
    if not fontFamilies:
        print("Error loading  font.")
        return None
    return fontFamilies[0]

def getDefaultFontPointSize() -> float:
    return QFont().pointSizeF()

def getMonospaceFont(scale: float = 1) -> QFont:
    global __monospaceFont
    if  __monospaceFont is None:
        __monospaceFont = QFont(_loadFont("Inconsolata-Regular.ttf"), getDefaultFontPointSize() * scale)
    return __monospaceFont

def getTextFont(scale: float = 1) -> QFont:
    global __variableWidthFont
    if  __variableWidthFont is None:
        __variableWidthFont = QFont(_loadFont("Roboto-Regular.ttf" ), getDefaultFontPointSize() * scale)
    return __variableWidthFont

def init() -> None:
    getMonospaceFont()
    getTextFont()
    for x in [ "Teko-Regular.ttf" ]:
        _loadFont(x)
