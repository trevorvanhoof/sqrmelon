from __future__ import annotations

import datetime
import math
import os
import sys
from typing import Any, Callable, ClassVar, Optional, TextIO

from plugin_host_app import PluginContext
from qt import QAction, QCloseEvent, QDockWidget, QHBoxLayout, QHideEvent, QLabel, QMainWindow, QPixmap, QProgressBar, QSettings, QShowEvent, QStyle, Qt, QTextCursor, QTextEdit, QWidget

from editor_core_ui.style_manager import DEFAULT_FIXED_WIDTH_FONT, StyleManager


class EditorWindow(QMainWindow):
    """
    Editor main window.
    """

    beforeCloseEvent: Callable[[QCloseEvent], bool] = None

    def __init__(self, styleManager: StyleManager, settings: QSettings, cancellationToken: object, name: Optional[str] = None) -> None:
        """
        Initialize this instance.
        Parameters:
            styleManager (StyleManager): Visual theme manager.
            settings (QSettings): Application settings.
            name (Optional[str]): When not None, instance name to persist data between sessions.
        """
        assert styleManager is not None
        assert settings is not None
        assert cancellationToken is not None

        super().__init__()
        self.__settings: QSettings = settings
        self.__cancellationToken = cancellationToken
        self.setObjectName(name or __class__.__name__)
        self.setAnimated(False)
        self.setDockNestingEnabled(True)
        self.setMinimumSize(1280, 720)
        self.setWindowIcon(QPixmap(os.path.join(os.path.dirname(__file__), "resources", 'Candy Cane-48.png' if datetime.datetime.month == '12' else 'SqrMelon.ico')))
        self.setWindowTitle("SqrMelon Fx")

        # Set up the status bar.
        self.statusLabel = QLabel("Ready.")
        self.statusProgressBar = QProgressBar()
        self.statusProgressBar.setMaximumHeight(16)
        self.statusProgressBar.setValue(0)
        self.statusProgressBar.setMaximum(100)
        self.statusProgressBar.setTextVisible(False)
        statusBarLayout = QHBoxLayout()
        statusBarLayout.addWidget(self.statusLabel, 3)
        statusBarLayout.addWidget(self.statusProgressBar, 1)
        statusBarLayout.setContentsMargins(12, 4, 4, 4)
        statusBarWidget = QWidget()
        statusBarWidget.setLayout(statusBarLayout)
        self.statusBar().setStyleSheet("* { border: none; background-color: transparent; } *::hover { background-color: transparent; }")         
        self.statusBar().addWidget(statusBarWidget, 1)

        # Set up the menu bar.
        menuBar  = self.menuBar()
        menuBar.setStyleSheet("""QMenu::indicator { background-color: transparent; }""")
        viewMenu = menuBar.addMenu("View")
        viewMenu_appearance = viewMenu.addMenu("Appearance")

        # Menu option: View/Appearance/Fullscreen.
        def updateFullScreen(checked: bool) -> None:
            if checked: self.showFullScreen() 
            else: self.showNormal()
        viewMenu_appearance_fsEditor = QAction("Fullscreen", self)
        viewMenu_appearance_fsEditor.setCheckable(True)
        viewMenu_appearance_fsEditor.setChecked(self.isFullScreen())
        viewMenu_appearance_fsEditor.setShortcut("Shift+F11")
        viewMenu_appearance_fsEditor.triggered.connect(updateFullScreen)
        viewMenu_appearance.addAction(viewMenu_appearance_fsEditor)        

        # Menu option: View/Appearance/Use dark theme.
        def updateDarkStyle(checked: bool) -> None: styleManager.darkStyle = checked
        viewMenu_appearance_darkTheme = QAction("Use dark theme", self)
        viewMenu_appearance_darkTheme.setCheckable(True)
        viewMenu_appearance_darkTheme.setChecked(styleManager.darkStyle)
        viewMenu_appearance_darkTheme.triggered.connect(updateDarkStyle)
        viewMenu_appearance.addAction(viewMenu_appearance_darkTheme)

        # Base layout.
        debugLogWidgetDock: QDockWidget = self.dockWidget(EditorWindow._DebugLog.create(styleManager), 'Python log', where=Qt.DockWidgetArea.TopDockWidgetArea)

        # Handle style changes that involve pixmap updates.
        def styleChanged(darkStyleEnabled: bool, uncommittedIcons: list[tuple[QPixmap, int]]) -> None:
            uncommittedIconsMap: dict[int, QPixmap] = {key: pixmap for pixmap, key in uncommittedIcons}
            for i in self.findChildren(QWidget, options = Qt.FindChildOption.FindChildrenRecursively):
                if isinstance(i, QLabel):
                    k: int = i.pixmap().cacheKey()
                    if k in uncommittedIconsMap:
                        i.setPixmap(uncommittedIconsMap[k])
        styleManager.styleChanged.connect(styleChanged)

    def closeEvent(self, event: QCloseEvent):
        """
        Close the window if no "beforeCloseEvent" handler exists, or it exists and returned True.
        Parameters:
            event (QCloseEvent): Event received.
        """
        eventAccepted: bool = self.beforeCloseEvent(event) if self.beforeCloseEvent else True
        if eventAccepted:
            event.accept()
            self.__cancellationToken.cancel()
        else:
            event.ignore()

    def showEvent(self, event: QShowEvent) -> None:
        """
        Show the window.
        Parameters:
            event (QShowEvent): Event received.
        """
        r = self.__settings.value('%s/geometry' % self.objectName(), None)
        s = self.__settings.value('%s/state'    % self.objectName(), None)
        if r is not None: self.restoreGeometry(r)
        if s is not None: self.restoreState   (s)

    def hideEvent(self, event: QHideEvent) -> None:
        """
        Hide the window.
        Parameters:
            event (QHideEvent): Event received.
        """
        self.__settings.setValue('%s/geometry' % self.objectName(), self.saveGeometry())
        self.__settings.setValue('%s/state'    % self.objectName(), self.saveState   ())

    def dockWidget(self, widget: QWidget, name: Optional[str] = None, where: Qt.DockWidgetArea = Qt.DockWidgetArea.RightDockWidgetArea,
        direction: Qt.Orientation = Qt.Orientation.Horizontal) -> QDockWidget:
        """
        Wrap the given widget into a QDockWidget and dock it in the current
        window.
        Parameters:
            widget (QWidget): The widget to dock.
            name (Optional[str]): Name for the widget. Will be displayed in the docked widget title bar.
            where (Qt.DocWidgetArea): Dock area to attach the widget to.
            direction (Qt.Orientation): Dock area orientation.
        Returns:
            QDockWidget: Resulting dock widget.
        """
        assert widget is not None

        name = name or widget.__class__.__name__
        dock = QDockWidget(self)

        dock.setObjectName(name)
        dock.setWidget(widget)
        dock.setWindowTitle(name)
        dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetVerticalTitleBar)
        self.addDockWidget(where, dock, direction)

        return dock


    class _DebugLog(object):
        """
        Debug log console widget that redirects print() output to 
        """

        __prevStdOut: ClassVar[TextIO | Any] = None
        __prevStdErr: ClassVar[TextIO | Any] = None

        class DebugLogWidget(QTextEdit):
            def __init__(self):
                super().__init__()
                
            def contextMenuEvent(self, event: Any) -> None:
                menu = self.createStandardContextMenu()
                custom_action = QAction("Clear", self)
                custom_action.triggered.connect(self.custom_action_triggered)
                custom_action.setIcon(PluginContext.instance().style().standardIcon(QStyle.SP_LineEditClearButton))
                menu.addAction(custom_action)
                menu.exec(event.globalPos())
            
            def custom_action_triggered(self):
                self.setHtml("")

        def __init__(self, textEditWidget: QTextEdit, fwd: TextIO) -> None:
            """
            """
            assert textEditWidget is not None
            assert fwd is not None

            self.__textEditWidget = textEditWidget
            self.__fwd = fwd

        def write(self, text: str) -> None:
            """
            """
            
            self.__textEditWidget.moveCursor(QTextCursor.MoveOperation.End)
            if text not in [ '\n', '\r' ]:
                
                okColor : str = "#4caf50"
                wrnColor: str = "#ffa94d"
                errColor: str = "#ff5a5a"

                text = text.replace('\n', '<br/>').replace('\r', '<br/>')
                beautifiedText: str = "<span style=\""
                beautifiedText += f"color: {okColor}" if text.startswith("[OK ]") else f"color: {wrnColor}" if text.startswith("[WRN]") else f"color: {errColor}" if text.startswith("[ERR]") else ""
                beautifiedText += "\">"
                beautifiedText += text[5:] if text[:5] in [ "[INF]", "[OK ]", "[WRN]", "[ERR]" ] else text
                beautifiedText += "</span>"
                self.__textEditWidget.insertHtml(beautifiedText)
            else:
                self.__textEditWidget.insertHtml("<br/>")
            self.__fwd.write(text)

        @staticmethod
        def create(styleManager: StyleManager) -> QTextEdit:
            """
            """
            assert styleManager is not None

            EditorWindow._DebugLog.__prevStdOut = sys.stdout
            EditorWindow._DebugLog.__prevStdErr = sys.stderr

            textEditWidget = EditorWindow._DebugLog.DebugLogWidget()
            textEditWidget.setStyleSheet(textEditWidget.styleSheet() +
                """* { font-family: '""" + DEFAULT_FIXED_WIDTH_FONT + """'; font-size: """ + str(int(math.ceil(styleManager.fontPointSize * 1.1))) +  """pt; }""")
            textEditWidget.setReadOnly(True)

            sys.stdout = EditorWindow._DebugLog(textEditWidget, sys.stdout)
            sys.stderr = EditorWindow._DebugLog(textEditWidget, sys.stderr)
            return textEditWidget

        @staticmethod
        def destroy() -> None:
            sys.stdout = EditorWindow._DebugLog.__prevStdOut
            sys.stderr = EditorWindow._DebugLog.__prevStdErr

