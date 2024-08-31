import datetime
import functools
import os
import shutil
import sys
import traceback
from typing import Any, cast, Optional, TextIO

import icons
from animationgraph.curveview import CurveEditor
from camerawidget import Camera
from fileutil import FileDialog, FilePath
from overlays import Overlays
from profileui import Profiler
from projutil import currentProjectDirectory, currentProjectFilePath, currentScenesDirectory, gSettings, PROJ_EXT, SCENE_EXT, setCurrentProjectFilePath
from qt import *
from qtutil import QMainWindowState
from scene import Scene
from scenelist import SceneList
from sceneview3d import execfile, SceneView
from shots import Shot, ShotManager
from timeslider import Timer, TimeSlider

IGNORED_EXTENSIONS = (PROJ_EXT, '.user')
DEFAULT_PROJECT = 'defaultproject'
FFMPEG_PATH = 'ffmpeg.exe'


class PyDebugLog:
    """Small utility to reroute the python print output to a QTextEdit."""

    def __init__(self, edit: QTextEdit, fwd: TextIO) -> None:
        self.__edit = edit
        self.__fwd = fwd

    def write(self, text: str) -> None:
        self.__edit.moveCursor(QTextCursor.MoveOperation.End)
        self.__edit.insertPlainText(text)
        self.__fwd.write(text)

    @staticmethod
    def create() -> QTextEdit:
        edit = QTextEdit()
        sys.stdout = PyDebugLog(edit, sys.stdout)  # type: ignore
        sys.stderr = PyDebugLog(edit, sys.stderr)  # type: ignore
        return edit


class App(QMainWindowState):
    def __init__(self) -> None:
        super(App, self).__init__(gSettings)
        self.setAnimated(False)

        if datetime.datetime.month == '12':
            self.setWindowIcon(icons.get('Candy Cane-48'))
        else:
            self.setWindowIcon(icons.get('SqrMelon'))
        self.setWindowTitle('SqrMelon (Architect Edition)')
        self.setDockNestingEnabled(True)

        self.__menuBar = QMenuBar()
        self.setMenuBar(self.__menuBar)

        self.__dockWidgetMenu = QMenu('Components')

        self.__statusBar = QStatusBar()
        self.setStatusBar(self.__statusBar)

        self._timer = Timer()
        self.__shotsManager = ShotManager()
        self.__shotsManager.viewShotAction.connect(self.__onViewShot)
        self.__graphEditor = CurveEditor(self._timer)
        self.__shotsManager.currentChanged.connect(self.__graphEditor.setShot)
        self.__overlays = Overlays()
        self.__sceneView = SceneView(self.__shotsManager, self._timer, self.__overlays)
        self.__overlays.changed.connect(self.__sceneView.update)
        self._timer.timeChanged.connect(self.__setCurrentShot)
        self.__shotsManager.shotPinned.connect(self.__setCurrentShot)
        self.__shotsManager.shotsEnabled.connect(self.__setCurrentShot)
        self.__shotsManager.shotsDisabled.connect(self.__setCurrentShot)

        cameraView = Camera(self.__shotsManager, self.__graphEditor, self._timer)
        cameraView.cameraChanged.connect(self.__sceneView.update)
        self.__graphEditor.requestPositionKey.connect(cameraView.forwardPositionKey)
        self.__graphEditor.requestRotationKey.connect(cameraView.forwardRotationKey)
        self.__sceneView.setCamera(cameraView)
        self.__projectMenu = self.__menuBar.addMenu('&Project')
        self.__projectMenu.addAction('&New').triggered.connect(self.__onNewProject)
        self.__projectMenu.addAction('&Open').triggered.connect(self.__onOpenProject)
        save = self.__projectMenu.addAction('&Save')
        save.setShortcut(QKeySequence.StandardKey.Save)
        save.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        save.triggered.connect(self.__onCtrlS)
        self.__sceneList = SceneList(self.__shotsManager)
        self.__shotsManager.findSceneRequest.connect(self.__sceneList.selectSceneWithName)
        self.__sceneList.requestCreateShot.connect(self.__shotsManager.createShot)
        self.__sceneList.setEnabled(False)

        self.__profiler = Profiler()

        self.timeSlider = TimeSlider(self._timer, self.__shotsManager)
        self.__shotsManager.shotChanged.connect(self.timeSlider.update)

        self._addDockWidget(self.__sceneList, where=Qt.DockWidgetArea.TopDockWidgetArea)
        self._addDockWidget(self.__shotsManager, where=Qt.DockWidgetArea.TopDockWidgetArea)
        # In PySide6 something goes wrong when we enable a scene while the view is already visible.
        # For that reason we have to use this trick where scene view inherits QOpenGLWindow
        # instead of QOpenGLWidget, because that one does not have this bug.
        # I believe this is related to Qt's composition of widgets, a window container ditches
        # a ton of features that I think started interfering with our rendering code.
        window = self.createWindowContainer(self.__sceneView, self)
        window.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        viewDock = self._addDockWidget(window, '3D View', where=Qt.DockWidgetArea.TopDockWidgetArea)
        self.__viewDock = viewDock  # Need this for F11 feature
        self.__restoreFullScreenInfo: Optional[tuple[QSize, bool]] = None
        logDock = self._addDockWidget(PyDebugLog.create(), 'Python log', where=Qt.DockWidgetArea.TopDockWidgetArea)
        self.tabifyDockWidget(logDock, viewDock)

        self._addDockWidget(self.timeSlider, where=Qt.DockWidgetArea.LeftDockWidgetArea)
        cameraDock = self._addDockWidget(cameraView, where=Qt.DockWidgetArea.LeftDockWidgetArea)
        overlayDock = self._addDockWidget(self.__overlays, 'Overlays', Qt.DockWidgetArea.LeftDockWidgetArea)
        self.tabifyDockWidget(overlayDock, cameraDock)

        self._addDockWidget(self.__graphEditor, where=Qt.DockWidgetArea.BottomDockWidgetArea)
        self._addDockWidget(self.__profiler, where=Qt.DockWidgetArea.BottomDockWidgetArea, direction=Qt.Orientation.Vertical)

        self.__initializeProject()

        undoStack, cameraUndoStack = self.__graphEditor.undoStacks()
        undo = undoStack.createUndoAction(self, '&Undo')
        undo.setShortcut(QKeySequence.StandardKey.Undo)
        undo.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)

        redo = undoStack.createRedoAction(self, '&Redo')
        redo.setShortcut(QKeySequence.StandardKey.Redo)
        redo.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)

        camUndo = cameraUndoStack.createUndoAction(self, 'Undo')
        camUndo.setShortcut(QKeySequence('['))
        camUndo.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)

        camRedo = cameraUndoStack.createRedoAction(self, 'Redo')
        camRedo.setShortcut(QKeySequence(']'))
        camRedo.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)

        camKey = QAction('&Key camera', self)
        camKey.setShortcut(QKeySequence(Qt.Key.Key_K))
        camKey.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        camKey.triggered.connect(cameraView.insertKey)

        camToggle = QAction('&Toggle camera control', self)
        camToggle.setShortcut(QKeySequence(Qt.Key.Key_T))
        camToggle.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        camToggle.triggered.connect(cameraView.toggle)

        camCopAnim = QAction('Snap came&ra to animation', self)
        camCopAnim.setShortcut(QKeySequence(Qt.Key.Key_R))
        camCopAnim.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        camCopAnim.triggered.connect(cameraView.copyAnim)

        self.__editMenu = self.__menuBar.addMenu('Edit')
        self.__editMenu.addAction(undo)
        self.__editMenu.addAction(redo)
        self.__editMenu.addAction(camUndo)
        self.__editMenu.addAction(camRedo)
        self.__editMenu.addSeparator()
        self.__editMenu.addAction(camKey)
        self.__editMenu.addAction(camToggle)
        self.__editMenu.addAction(camCopAnim)

        toolsMenu = self.__menuBar.addMenu('Tools')
        toolsMenu.addAction('Color Picker').triggered.connect(self.__colorPicker)

        lock = toolsMenu.addAction('Lock UI')
        lock.setCheckable(True)
        lock.toggled.connect(self.__toggleUILock)

        fs = toolsMenu.addAction('Full screen viewport')
        fs.setShortcut(QKeySequence(Qt.Key.Key_F11))
        fs.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        fs.triggered.connect(self.__fullScreenViewport)

        self.__previewMenu = toolsMenu.addMenu('Preview resolution')
        previewRadioGroup = QActionGroup(self)
        # add action & connect it to the setPreviewRes with right parameters
        hd = self.__previewMenu.addAction('1080p (HD)')
        hd.triggered.connect(functools.partial(self.__sceneView.setPreviewRes, 1920, 1080, 1.0))
        hd.setCheckable(True)
        hd.setActionGroup(previewRadioGroup)
        hdready = self.__previewMenu.addAction('720p')
        hdready.triggered.connect(functools.partial(self.__sceneView.setPreviewRes, 1280, 720, 1.0))
        hdready.setCheckable(True)
        hdready.setActionGroup(previewRadioGroup)
        sdready = self.__previewMenu.addAction('480p')
        sdready.triggered.connect(functools.partial(self.__sceneView.setPreviewRes, 854, 480, 1.0))
        sdready.setCheckable(True)
        sdready.setActionGroup(previewRadioGroup)

        saveStatic = toolsMenu.addAction('Save static textures')
        saveStatic.triggered.connect(self.__sceneView.saveStaticTextures)

        viewport = self.__previewMenu.addAction('Viewport')
        viewport.triggered.connect(functools.partial(self.__sceneView.setPreviewRes, None, None, 1.0))
        viewport.setCheckable(True)
        viewport.setActionGroup(previewRadioGroup)
        half = self.__previewMenu.addAction('1/2 view')
        half.triggered.connect(functools.partial(self.__sceneView.setPreviewRes, None, None, 0.5))
        half.setCheckable(True)
        half.setActionGroup(previewRadioGroup)
        quart = self.__previewMenu.addAction('1/4 view')
        quart.triggered.connect(functools.partial(self.__sceneView.setPreviewRes, None, None, 0.25))
        quart.setCheckable(True)
        quart.setActionGroup(previewRadioGroup)
        eight = self.__previewMenu.addAction('1/8 view')
        eight.triggered.connect(functools.partial(self.__sceneView.setPreviewRes, None, None, 0.125))
        eight.setCheckable(True)
        eight.setActionGroup(previewRadioGroup)

        toolsMenu.addAction('Record').triggered.connect(self.__record)

        option = viewport
        if gSettings.contains('GLViewScale'):
            viewScale = float(gSettings.value('GLViewScale'))  # type: ignore
            option = {1.0: viewport, 0.5: half, 0.25: quart, 0.125: eight}[viewScale]
        option.setChecked(True)

        self.__menuBar.addMenu(self.__dockWidgetMenu)
        self.__menuBar.addAction('About').triggered.connect(self.__aboutDialog)
        self.__restoreUiLock(lock)

    def _addDockWidget(self, widget: QWidget, name: Optional[str] = None, where: Qt.DockWidgetArea = Qt.DockWidgetArea.RightDockWidgetArea, direction: Qt.Orientation = Qt.Orientation.Horizontal) -> QDockWidget:
        dockWidget = super(App, self)._addDockWidget(widget, name, where, direction)
        self.__dockWidgetMenu.addAction(dockWidget.toggleViewAction())
        return dockWidget

    def __record(self) -> None:
        diag = QDialog()
        fId = int(gSettings.value('RecordFPS', 2))  # type: ignore
        rId = int(gSettings.value('RecordResolution', 3))  # type: ignore
        layout = QGridLayout()
        diag.setLayout(layout)
        layout.addWidget(QLabel('FPS: '), 0, 0)
        fps = QComboBox()
        fps.addItems(['12', '24', '30', '48', '60', '120'])
        fps.setCurrentIndex(fId)
        layout.addWidget(fps, 0, 1)
        layout.addWidget(QLabel('Vertical resolution: '), 1, 0)
        resolution = QComboBox()
        resolution.addItems(['144', '288', '360', '720', '1080', '2160'])
        resolution.setCurrentIndex(rId)
        layout.addWidget(resolution, 1, 1)
        ok = QPushButton('Ok')
        ok.clicked.connect(diag.accept)
        cancel = QPushButton('Cancel')
        cancel.clicked.connect(diag.reject)
        layout.addWidget(ok, 2, 0)
        layout.addWidget(cancel, 2, 1)
        diag.exec()
        if diag.result() != QDialog.DialogCode.Accepted:
            return
        gSettings.setValue('RecordFPS', fps.currentIndex())
        gSettings.setValue('RecordResolution', resolution.currentIndex())

        FPS = int(fps.currentText())
        HEIGHT = int(resolution.currentText())
        WIDTH = (HEIGHT * 16) // 9
        FMT = 'jpg'

        data = b'\0' * (WIDTH * HEIGHT * 3)
        flooredStart = self._timer.secondsToBeats(int(self._timer.beatsToSeconds(self._timer.start) * FPS) / float(FPS))
        duration = self._timer.beatsToSeconds(self._timer.end - flooredStart)

        captureDir = currentProjectDirectory().join('capture')
        captureDir.ensureExists(isFolder=True)

        progress = QProgressDialog(self)
        progress.setMaximum(int(duration * FPS))
        prevFrame = 0

        for frame in range(int(duration * FPS)):
            deltaTime = (frame - prevFrame) / float(FPS)
            prevFrame = frame
            progress.setValue(frame)
            QApplication.processEvents()
            if progress.wasCanceled():
                break

            beats = flooredStart + self._timer.secondsToBeats(frame / float(FPS))

            shot = self.__shotsManager.shotAtTime(beats)
            if shot is None:
                continue
            sceneFile = currentScenesDirectory().join(shot.sceneName).ensureExt(SCENE_EXT)
            self.__sceneView.makeCurrent()
            scene = Scene.getScene(sceneFile)
            scene.setSize(WIDTH, HEIGHT)

            uniforms = self.__shotsManager.evaluate(beats)
            textureUniforms = self.__shotsManager.additionalTextures(beats)
            uOrigin = uniforms['uOrigin']
            uAngles = uniforms['uAngles']
            assert isinstance(uOrigin, list)
            assert isinstance(uAngles, list)
            self.__sceneView.cameraInput().setData(*(uOrigin + uAngles))  # feed animation into camera so animationprocessor can read it again
            cameraData = self.__sceneView.cameraInput().data()

            modifier = currentProjectDirectory().join('animationprocessor.py')
            if modifier.exists():
                execfile(str(modifier), globals(), locals())

            uniforms.update(self.__sceneView.textureUniforms())

            scene.drawToScreen(self._timer.beatsToSeconds(beats), beats, uniforms, (0, 0, WIDTH, HEIGHT), textureUniforms)
            scene.colorBuffers[-1][0].use()

            from OpenGL.GL import glGetTexImage, GL_TEXTURE_2D, GL_RGB, GL_UNSIGNED_BYTE
            glGetTexImage(GL_TEXTURE_2D, 0, GL_RGB, GL_UNSIGNED_BYTE, data)

            captureDir = currentProjectDirectory().join('capture')
            img = QImage(data, WIDTH, HEIGHT, QImage.Format.Format_RGB888)
            img.mirror(False, True)
            img.save(captureDir.join('dump_%s_%05d.%s' % (FPS, int(self._timer.beatsToSeconds(self._timer.start) * FPS) + frame, FMT)))

        progress.close()

        convertCaptureDir = currentProjectDirectory().join('convertcapture')
        convertCaptureDir.ensureExists(isFolder=True)

        with convertCaptureDir.join('convert.bat').edit() as fh:
            start = ''
            start2 = ''
            if int(self._timer.start * FPS) > 0:
                start = '-start_number {} '.format(int(self._timer.beatsToSeconds(self._timer.start) * FPS))
                start2 = '-vframes {} '.format(int(self._timer.beatsToSeconds(self._timer.end - self._timer.start) * FPS))

            fh.write('cd "../capture"\n"{}" -framerate {} {}-i dump_{}_%%05d.{} {}-c:v libx264 -r {} -pix_fmt yuv420p "../convertcapture/output.mp4"'.format(FFMPEG_PATH, FPS, start, FPS, FMT, start2, FPS))

        with convertCaptureDir.join('convertGif.bat').edit() as fh:
            start = ''
            start2 = ''
            iln = ''
            if int(self._timer.start * FPS) > 0:
                start = '-start_number {} '.format(int(self._timer.beatsToSeconds(self._timer.start) * FPS))
                start2 = '-vframes {} '.format(int(self._timer.beatsToSeconds(self._timer.end - self._timer.start) * FPS))
                iln = '-t {:03f} '.format(self._timer.beatsToSeconds(self._timer.end - self._timer.start))
            fh.write('REM File format is actually %5d but in a .bat file we need to escape % or something, so you can\'t copy paste this into a cmd prompt without fixing up the %%05d to be %5d.\n')
            fh.write('cd "../capture"\n"{}" -framerate {} {}{}-i dump_{}_%%05d.{} -vf "fps={},scale={}:-1:flags=lanczos,palettegen" palette.png\n'.format(FFMPEG_PATH, FPS, start, iln, FPS, FMT, FPS, HEIGHT))
            fh.write('"{}" -framerate {} {}-i dump_{}_%%05d.{} -i "palette.png" -filter_complex "fps=12,scale=360:-1:flags=lanczos[x];[x][1:v]paletteuse" {}-r {} "../convertcapture/output.gif"'.format(FFMPEG_PATH, FPS, start, FPS, FMT, start2, FPS))

        sound = self.timeSlider.soundtrackPath()
        if not sound:
            return

        with convertCaptureDir.join('merge.bat').edit() as fh:
            startSeconds = self._timer.beatsToSeconds(self._timer.start)
            cast(TextIO, fh).write('{} -i output.mp4 -itsoffset {} -i "{}" -vcodec copy -shortest merged.mp4'.format(FFMPEG_PATH, -startSeconds, sound))

    def __restoreUiLock(self, action: QAction) -> None:
        state = True if gSettings.value('lockui', '0') == '1' else False
        action.setChecked(state)
        features = QDockWidget.DockWidgetFeature(0 if state else 0b1111)
        for dockWidget in self.findChildren(QDockWidget):
            dockWidget.setFeatures(features)

    def __fullScreenViewport(self, *_: Any) -> None:
        # force floating
        dockWidget = self.__viewDock

        if not dockWidget.isFullScreen():
            floating = dockWidget.isFloating()
            self.__restoreFullScreenInfo = dockWidget.size(), floating
            if not floating:
                dockWidget.setFloating(True)
            dockWidget.showFullScreen()
        else:
            assert self.__restoreFullScreenInfo is not None
            dockWidget.showNormal()
            if dockWidget.isFloating() != self.__restoreFullScreenInfo[1]:
                dockWidget.setFloating(self.__restoreFullScreenInfo[1])
            if dockWidget.isFloating():
                dockWidget.resize(self.__restoreFullScreenInfo[0])

    def __toggleUILock(self, state: bool) -> None:
        gSettings.setValue('lockui', '1' if state else '0')
        features = QDockWidget.DockWidgetFeature(0 if state else 0b1111)
        for dockWidget in self.findChildren(QDockWidget):
            # only affect docked widgets
            if not dockWidget.isFloating():
                dockWidget.setFeatures(features)

    def __onViewShot(self, start: float, end: float, shot: Shot) -> None:
        self._timer.start = start
        if shot.pinned:
            self._timer.end = end
        else:
            self._timer.end = end - 0.01

    def __aboutDialog(self) -> None:
        QMessageBox.about(self, 'About SqrMelon',
                          r"""<p>SqrMelon is a tool to manage a versions (scenes) of a graph of fragment shaders (templates) & drive uniforms with animation curves (shots).</p>
                          <p>Download or find documentation on <a href="https://github.com/trevorvanhoof/sqrmelon/">GitHub/</a>!</p>
                          <p>Icons from <a href="https://icons8.com/">icons8.com/</a></p>""")

    @staticmethod
    def __colorPicker() -> None:
        color = QColorDialog.getColor()
        colorStr = f"vec3({str(round(color.red() / 255.0, 2))}, {str(round(color.green() / 255.0, 2))}, {str(round(color.blue() / 255.0, 2))})"
        cb = QApplication.clipboard()
        cb.setText(colorStr, mode=QClipboard.Mode.Clipboard)

    def __onCtrlS(self) -> None:
        if QApplication.focusWidget() != self.__sceneView:
            self.saveProject()
        else:
            self.__sceneView.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier))

    def saveProject(self) -> None:
        self.__sceneView.saveCameraData()
        self.__shotsManager.saveAllShots()
        self._timer.saveState()
        QMessageBox.information(self, 'Save succesful!', 'Animation, shot & timing changes have been saved.')

    def closeEvent(self, event: QCloseEvent) -> None:
        res = QMessageBox.question(self, 'Save before exit?', 'Do you want to save?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
        if res == QMessageBox.StandardButton.Cancel:
            event.ignore()
            return
        if res == QMessageBox.StandardButton.Yes:
            self.saveProject()
        self._store()

    def __setCurrentShot(self, *_: Any) -> None:
        shot = self.__shotsManager.shotAtTime(self._timer.time)
        if shot is None:
            self.__sceneView.setScene(None)
            self.__profiler.setScene(None)
            return
        sceneFile = currentScenesDirectory().join(shot.sceneName + SCENE_EXT)
        sc = Scene.getScene(sceneFile)
        self.__sceneView.setScene(sc)
        self.__profiler.setScene(sc)

    def __openProject(self, path: str) -> None:
        setCurrentProjectFilePath(FilePath(path))
        self.__sceneList.projectOpened()
        self.__shotsManager.projectOpened()
        self._timer.projectOpened()
        self.timeSlider.projectOpened()

    def __initializeProject(self) -> None:
        # If project file was specified by the command line, open it, otherwise reuse last opened.
        project = FilePath(sys.argv[1].strip('\'').strip('"')) if len(sys.argv) > 1 else currentProjectFilePath()

        if project is not None:
            if project.exists():
                self.__openProject(project)
                return
        projectFiles = [projFile for projFile in list(os.listdir(os.getcwd())) if projFile and projFile.endswith(PROJ_EXT)]
        if projectFiles:
            self.__openProject(os.path.join(os.getcwd(), projectFiles[0]))
            return

    def __changeProjectHelper(self, title: str) -> Optional[FilePath]:
        """
        Utility that shows a dialog if we're changing projects with potentially unsaved changes.
        Returns the current project directory, or the current working directory if no such project.
        """
        currentPath = FilePath(os.getcwd())

        project = currentProjectFilePath()
        if project is not None:
            # propose to save near current project
            folder = project.parent()
            if folder.exists():
                currentPath = folder

            # check if unsaved changes
            if QMessageBox.StandardButton.No == QMessageBox.warning(self, title, 'Any unsaved changes will be lost. Continue?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No):
                return None

        return currentPath

    def __onNewProject(self) -> None:
        currentPath = self.__changeProjectHelper('Creating new project')
        if not currentPath:
            return
        res = FileDialog.getSaveFileName(self, 'Create new project', currentPath, 'Project folder')
        if not res:
            return
        shutil.copytree(DEFAULT_PROJECT, res, ignore=lambda p, f: [] if os.path.basename(p).lower() == 'Scenes' else [n for n in f if os.path.splitext(n)[-1].lower() in IGNORED_EXTENSIONS])
        projectFile = FilePath(res).join(os.path.basename(res) + PROJ_EXT)
        projectFile.ensureExists()
        self.__openProject(projectFile)

    def __onOpenProject(self) -> None:
        currentPath = self.__changeProjectHelper('Changing project')
        if not currentPath:
            return
        res = FileDialog.getOpenFileName(self, 'Open project', currentPath, f'Project files (*{PROJ_EXT})')
        if not res:
            return
        self.__openProject(res)


def run() -> None:
    # We found that not setting a version in Ubuntu didn't work
    glFormat = QSurfaceFormat()
    glFormat.setVersion(4, 6)
    glFormat.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    glFormat.setDefaultFormat(glFormat)

    # We found that Qt started destroying OpenGL contexts
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = App()
    win.show()

    print("Qt version: ", qVersion(), ".")
    app.exec()


if __name__ == '__main__':
    # import profileutil
    # profileutil.runctx('run()', globals(), locals(), executable=profileutil.QCACHEGRIND)
    try:
        run()
    except:
        QMessageBox.critical(None, 'Unhandled exception', traceback.format_exc())
