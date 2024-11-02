from collections import namedtuple
import glob
import math
import os
import threading
from typing import ClassVar, Optional

from plugin_host_app import PluginContext
from qt import QCoreApplication, QFont, QFontDatabase, QObject, QPixmap, Signal
import qdarktheme


DEFAULT_VARIABLE_WIDTH_FONT: str = "roboto"
DEFAULT_VARIABLE_WIDTH_VERTICAL_FONT: str = "teko"
DEFAULT_FIXED_WIDTH_FONT: str = "inconsolata"
_RESOURCE_INCLUDED_EXTENSIONS: list[str] = [ ".ttf",  ".svg", ".png", ".ico" ]


class ResourceAlreadyExistsException(Exception): ...
class ResourceFormatException (Exception): ...
class IncompleteStyleException(Exception): ...


class StyleManager(QObject):
    """
    Manage resources such as fonts, icons, and images.
    Editor code resources are stored in "./resources". Fonts and icons in this directory load by default and cannot be 
    unloaded.
    You can mount additional source folders to add resources (e.g., for plugins). Basic theming supports light and dark
    modes. Images in "dark" or "light" subfolders are automatically handled as themed resources. Theming does not apply
    to fonts.
    Subfolders beyond "light" and "dark" are not supported. Assets are organized by namespaces to avoid name conflicts.
    This plugin built-in assets have no namespace, while other plugin sources should use a local plugin namespace.
    """

    styleChanged: ClassVar[Signal] = Signal(bool, list) # darkStyleEnabled, [[pixmap, prevCacheKey]].

    __FontInfo = namedtuple("__FontInfo", [ "source", "fn", "fontFamily", "fontId"   ])
    __IconInfo = namedtuple("__IconInfo", [ "source", "fn", "pixmap", "prevCacheKey" ])

    def __init__(self, minimalResourcesPath: str, darkStyleEnabled: bool = True) -> None:
        """
        Initialize the style manager.
        Parameters:
            minimalResourcePath (str): Path to the default resources folder.
            darkStyleEnabled (bool): True to enable dark mode by default; False otherwise.
        """
        assert minimalResourcesPath is not None
        super().__init__()

        self.__styleManagerLock: threading.Lock = threading.Lock()
        self.__style: str = None
        self.__fontCache: dict[str, StyleManager.__FontInfo] = {}
        self.__iconCache: dict[str, StyleManager.__IconInfo] = {}
        self.__sources: dict[str, str] = {} # Source -> Namespace.

        self.__setDarkStyle(darkStyleEnabled)
        self.addSource(minimalResourcesPath, None)

    def addSource(self, source: str, namespace: Optional[str] = None) -> None:
        """
        Adds a resource source to the style manager.
        Scans the directory for fonts, icons and images and loads them. If present, subdirectories "light" and "dark" 
        are scanned to incorporate stylized versions of the icons and images for light and dark modes.
        Parameters:
            source (str): Path to the source directory containing resources to be scanned.
            namespace (Optional[str]): For non-core sources (e.g., those from plugins), namespace to avoid name
                conflicts. Asset IDs will be a combination of the namespace and the resource filename without the
                extension.
        Raises:
            ResourceAlreadyExistsException: Font or icon is already present under the same namespace.
            ResourceFormatException: Font or icon file format is not recognized.
       """
        assert source is not None
        assert os.path.basename(os.path.dirname(source)) not in [ "light", "dark" ]
        assert os.path.isdir(source)

        source = PluginContext.normalizedPath(source)
        namespacePrefix = ((namespace + ".") if namespace is not None else "")
        if os.path.isdir(os.path.join(source, "dark")) != os.path.isdir(os.path.join(source, "light")):
            raise IncompleteStyleException(f'Style data at "{source}" is incomplete.')

        with self.__styleManagerLock:

            for fontPath in glob.glob(os.path.join(source, "*.ttf")):
                normalizedPath = PluginContext.normalizedPath(fontPath)
                self.__loadFont(normalizedPath, namespacePrefix, source)

            for d in [ source, PluginContext.normalizedPath(os.path.join(source, self.__style)) ]:
                for i in [ "*.svg", "*.png", "*.ico" ]:
                    for iconPath in glob.glob(os.path.join(d, i)):
                        normalizedPath = PluginContext.normalizedPath(iconPath)
                        self.__loadIcon(normalizedPath, namespacePrefix, source)

            self.__sources[source] = namespace
            PluginContext.instance().watchDirectory(source, self.__styleChanged, [], _RESOURCE_INCLUDED_EXTENSIONS)

    def removeSource(self, source: str) -> None:
        """
        Remove the resource source from the style manager. All resources associated to this source are freed.
        Parameters:
            source (str): Path to the source directory containing resources to be removed.
        """
        assert source is not None
        assert os.path.basename(os.path.dirname(source)) not in [ "light", "dark" ]

        source = PluginContext.normalizedPath(source)
        with self.__styleManagerLock:
            
            PluginContext.instance().unwatchDirectory(source)
            del self.__sources[source]

            toRemove: list[str] = []
            for k in [key for key, value in self.__fontCache.items() if value.source == source]: toRemove.append(k)
            for k in toRemove: del self.__fontCache[k]

            toRemove: list[str] = []
            for k in [key for key, value in self.__iconCache.items() if value.source == source]: toRemove.append(k)
            for k in toRemove: del self.__iconCache[k]

    @property
    def darkStyle(self) -> bool:
        """
        True if dark style is enabled; False if light is.
        """
        return self.__style == "dark"

    @darkStyle.setter
    def darkStyle(self, darkStyleEnabled: bool) -> None:
        """
        Enable or disable dark style.
        Changing this property will automatically update any affected resources associated with the current style.
        The style manager can't update in-place any QPixmap instances used by the application. To overcome that, the
        StyleManager.styleChanged signal is emitted when the change is completed, with the following arguments:
            arg0: StyleManager instance event sender.
            arg1: True if dark style has been enabled; False otherwise.
            arg2: List of tuples containing updated QPixmap + prev. QPixmap cache key (to perform in-place image
                updates in Qt widgets).
        Parameters:
            darkStyleEnabled (bool): True to enable dark style; False to enable light style.
        """
        self.__setDarkStyle(darkStyleEnabled)
        uncommittedIcons: list[tuple[QPixmap, int]] = []
        with self.__styleManagerLock:
            for k, v in self.__iconCache.items():
                if v.pixmap.cacheKey() != v.prevCacheKey:
                    uncommittedIcons.append([ v.pixmap, v.prevCacheKey ])
                    self.__iconCache[k] = v._replace(prevCacheKey = v.pixmap.cacheKey())
        self.styleChanged.emit(darkStyleEnabled, uncommittedIcons)

    def icon(self, canonicalIconName: str) -> QPixmap:
        """
        Get the given icon or pixmap.
        Parameters:
            canonicalIconName (str): The canonical icon name (including the namespace).
        Returns:
            QPixmap: Icon pixmap.
        """
        assert canonicalIconName is not None
        return self.__iconCache[canonicalIconName].pixmap

    def font(self, canonicalFontName: str, scale: float = 1) -> QFont:
        """
        Get the given font.
        Parameters:
            canonicalFontName (str): The canonical font name (including the namespace).
            scale (float): Font scale multiplier.
        Returns:
            QFont: Font. 
        """
        assert scale > 0
        return QFont(self.__fontCache[canonicalFontName].fontFamily, self.fontPointSize * scale)

    @property
    def fontPointSize(self) -> float:
        return QFont().pointSizeF()

    def __loadFont(self, normalizedFilePath: str, namespacePrefix: str, normalizedSource: str) -> str:
        """
        Load a font resource from the specified file.
        This function is not thread-safe.
        Parameters:
            normalizedFilePath (str): Path to the font file to be loaded.
            namespacePrefix (str): Prefix for the font identifier used to create a unique ID in combination with the resource filename.
            normalizedSource (str): Un-themed source path where the font is based.
        Returns:
            str: Font family name.
        Raises:
            ResourceAlreadyExistsException: Font is already present under the same namespace.
            ResourceFormatException: Font file format is not recognized.
        """
        assert normalizedFilePath is not None
        assert normalizedSource is not None
        assert os.path.isfile(normalizedFilePath)

        fnParts = os.path.splitext(normalizedFilePath)
        if (namedId := (namespacePrefix + os.path.basename(fnParts[0])).strip().lower()) in self.__fontCache:
            raise ResourceAlreadyExistsException(f'Font "{namedId}" already registered.')

        fontId = QFontDatabase.addApplicationFont(normalizedFilePath)
        if fontId == -1 or not (fontFamilies := QFontDatabase.applicationFontFamilies(fontId)):
            raise ResourceFormatException(f'Error loading font file "{normalizedFilePath}".')
        self.__fontCache[namedId] = StyleManager.__FontInfo(source = normalizedSource, fn = normalizedFilePath, fontFamily = fontFamilies[0], fontId = fontId)
        if namedId.endswith("-regular"):
            self.__fontCache[namedId.removesuffix("-regular")] = self.__fontCache[namedId]
        return fontFamilies[0]

    def __loadIcon(self, normalizedFilePath: str, namespacePrefix: str, normalizedSource: str) -> QPixmap:
        """
        Load a icon resource from the specified file. 
        This function is not thread-safe.
        Parameters:
            normalizedFilePath (str): Path to the icon file to be loaded.
            namespacePrefix (str): Prefix for the icon identifier used to create a unique ID in combination with the resource filename.
            normalizedSource (str): Un-themed source path where the icon is based.
        Returns:
            QPixmap: The QPixmap corresponding to the loaded image resource.
        Raises:
            ResourceAlreadyExistsException: Icon is already present under the same namespace.
            ResourceFormatException: Icon file format is not recognized.
        """
        assert normalizedFilePath is not None
        assert normalizedSource is not None
        assert os.path.isfile(normalizedFilePath)

        fnParts = os.path.splitext(normalizedFilePath)
        if (namedId := (namespacePrefix + os.path.basename(fnParts[0])).strip().lower()) in self.__iconCache:
            raise ResourceAlreadyExistsException(f'Font "{namedId}" already registered.')

        icon: QPixmap = QPixmap(normalizedFilePath)
        self.__iconCache[namedId] = StyleManager.__IconInfo(source = normalizedSource, fn = normalizedFilePath, pixmap = icon, prevCacheKey = None)
        return icon

    def __styleChanged(self, resourcePath: str) -> None:
        """
        If the resource in the given path has changed, reload it.
        Parameters:
            resourcePath (str): Absolute path to the resource that has been changed.
        """

        with self.__styleManagerLock:
            resourcePath = PluginContext.normalizedPath(resourcePath)
            k, v = next(((key, value) for key, value in self.__iconCache.items() if value.fn == resourcePath), (None, None))
            if v:
                if v.fn == resourcePath:
                    prevCacheKey = v.pixmap.cacheKey()
                    v.pixmap.load(resourcePath)
                    self.__iconCache[k] = self.__iconCache[k]._replace(fn = resourcePath, prevCacheKey = prevCacheKey)
            else:
                for k, v in self.__sources.items():
                    if k == resourcePath[:len(k)]:
                        self.__loadIcon(resourcePath, v or "", k)
                        break

        self.darkStyle = self.darkStyle # Force update.

    def __setDarkStyle(self, darkStyleEnabled: bool) -> None:
        """
        Enable or disable dark style.
        Changing this property will automatically update any affected resources associated with the current style.
        Parameters:
            darkStyleEnabled (bool): True to enable dark style; False to enable light style.
        """

        newStyle = "dark" if darkStyleEnabled else "light"
        if newStyle == self.__style:
            return
        
        def convertPathBetweenStyles(pathToConvert: str) -> str:
            pathToConvert = PluginContext.normalizedPath(pathToConvert)
            lastDirectory = os.path.basename(os.path.dirname(pathToConvert)).lower()
            fromStyle = "dark" if not darkStyleEnabled else "light"
            toStyle = "dark" if darkStyleEnabled else "light"
            if lastDirectory == fromStyle:
                needle = f"/{fromStyle}/"
                index = pathToConvert.rfind(needle)
                if index != -1:
                    return pathToConvert[:index] + f"/{toStyle}/" + pathToConvert[index + len(needle):]
            return pathToConvert

        with self.__styleManagerLock:
            for k, v in self.__iconCache.items():
                if (newPath := convertPathBetweenStyles(v.fn)) == v.fn:
                    continue

                prevCacheKey = v.pixmap.cacheKey()
                v.pixmap.load(newPath)
                self.__iconCache[k] = self.__iconCache[k]._replace(fn = newPath, prevCacheKey = prevCacheKey)

        qdarktheme.setup_theme(newStyle)
        QCoreApplication.instance().setStyleSheet(QCoreApplication.instance().styleSheet() + """
            *               { font-family: '""" + DEFAULT_VARIABLE_WIDTH_FONT          + """'; font-size: """ + str(int(math.ceil(self.fontPointSize * 1.0))) +  """pt; }
            QDockWidget     { font-family: '""" + DEFAULT_VARIABLE_WIDTH_VERTICAL_FONT + """'; font-size: """ + str(int(math.ceil(self.fontPointSize * 1.4))) +  """pt; }
            QMenuBar::item  { padding: 4px 10px; }                
            """
        )
        self.__style = newStyle
