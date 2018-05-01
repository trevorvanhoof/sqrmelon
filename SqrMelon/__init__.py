import os
import time
import sys
import shutil
import ctypes
import functools
import traceback

from camerawidget import Camera
from overlays import Overlays

from animationgraph.curveview import CurveEditor
from profileui import Profiler
from scene import Scene
from scenelist import SceneList
from sceneview3d import SceneView
from shots import ShotManager
from timeslider import Timer, TimeSlider
from util import PROJ_EXT, SCENE_EXT, gSettings, ScenesPath, ProjectDir
import fileutil
from qtutil import *
import icons

IGNORED_EXTENSIONS = (PROJ_EXT, '.user')
DEFAULT_PROJECT = 'defaultproject'


class PyDebugLog(object):
    """
    Small utility to reroute the python print output to a QTextEdit
    """

    def __init__(self, edit, fwd):
        self.__edit = edit
        self.__fwd = fwd

    def write(self, text):
        self.__edit.moveCursor(QTextCursor.End)
        self.__edit.insertPlainText(text)
        self.__fwd.write(text)

    @staticmethod
    def create():
        edit = QTextEdit()
        sys.stdout = PyDebugLog(edit, sys.stdout)
        sys.stderr = PyDebugLog(edit, sys.stderr)
        return edit


class App(QMainWindowState):
    def __init__(self):
        super(App, self).__init__(gSettings)
        self.setAnimated(False)
        month, day, year = time.strftime('%x').split('/')
        if month == '12':
            self.setWindowIcon(icons.get('Candy Cane'))
        else:
            self.setWindowIcon(icons.get('SqrMelon'))
        self.setWindowTitle('SqrMelon')
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
        self.__overlays.changed.connect(self.__sceneView.repaint)
        self._timer.timeChanged.connect(self.__setCurrentShot)
        self.__shotsManager.shotPinned.connect(self.__setCurrentShot)
        self.__shotsManager.shotsEnabled.connect(self.__setCurrentShot)
        self.__shotsManager.shotsDisabled.connect(self.__setCurrentShot)

        self.setCentralWidget(None)
        cameraView = Camera(self.__shotsManager, self.__graphEditor, self._timer)
        cameraView.cameraChanged.connect(self.__sceneView.repaint)
        self.__graphEditor.requestPositionKey.connect(cameraView.forwardPositionKey)
        self.__graphEditor.requestRotationKey.connect(cameraView.forwardRotationKey)
        self.__sceneView.setCamera(cameraView)
        self.__projectMenu = self.__menuBar.addMenu('&Project')
        self.__projectMenu.addAction('&New').triggered.connect(self.__onNewProject)
        self.__projectMenu.addAction('&Open').triggered.connect(self.__onOpenProject)
        save = self.__projectMenu.addAction('&Save')
        save.setShortcut(QKeySequence.Save)
        save.setShortcutContext(Qt.ApplicationShortcut)
        save.triggered.connect(self.__onCtrlS)
        self.__sceneList = SceneList()
        self.__shotsManager.findSceneRequest.connect(self.__sceneList.selectSceneWithName)
        self.__sceneList.requestCreateShot.connect(self.__shotsManager.createShot)
        self.__sceneList.setEnabled(False)
        self.__sceneList.setShotsManager(self.__shotsManager)

        self.__profiler = Profiler()

        self.timeSlider = TimeSlider(self._timer, self.__shotsManager)
        self.__shotsManager.shotChanged.connect(self.timeSlider.repaint)

        self._addDockWidget(self.__sceneList, where=Qt.TopDockWidgetArea)
        self._addDockWidget(self.__shotsManager, where=Qt.TopDockWidgetArea)
        viewDock = self._addDockWidget(self.__sceneView, '3D View', where=Qt.TopDockWidgetArea)
        logDock = self._addDockWidget(PyDebugLog.create(), 'Python log', where=Qt.TopDockWidgetArea)
        self.tabifyDockWidget(logDock, viewDock)

        self._addDockWidget(self.timeSlider, where=Qt.LeftDockWidgetArea)
        cameraDock = self._addDockWidget(cameraView, where=Qt.LeftDockWidgetArea)
        overlayDock = self._addDockWidget(self.__overlays, 'Overlays', Qt.LeftDockWidgetArea)
        self.tabifyDockWidget(overlayDock, cameraDock)

        self._addDockWidget(self.__graphEditor, where=Qt.BottomDockWidgetArea)
        self._addDockWidget(self.__profiler, where=Qt.BottomDockWidgetArea, direction=Qt.Vertical)

        self.__initializeProject()

        undoStack, cameraUndoStack = self.__graphEditor.undoStacks()
        undo = undoStack.createUndoAction(self, '&Undo')
        undo.setShortcut(QKeySequence.Undo)
        undo.setShortcutContext(Qt.ApplicationShortcut)

        redo = undoStack.createRedoAction(self, '&Redo')
        redo.setShortcuts(QKeySequence.Redo)
        redo.setShortcutContext(Qt.ApplicationShortcut)

        camUndo = cameraUndoStack.createUndoAction(self, 'Undo')
        camUndo.setShortcuts(QKeySequence('['))
        camUndo.setShortcutContext(Qt.ApplicationShortcut)

        camRedo = cameraUndoStack.createRedoAction(self, 'Redo')
        camRedo.setShortcuts(QKeySequence(']'))
        camRedo.setShortcutContext(Qt.ApplicationShortcut)

        camKey = QAction('&Key camera', self)
        camKey.setShortcuts(QKeySequence(Qt.Key_K))
        camKey.setShortcutContext(Qt.ApplicationShortcut)
        camKey.triggered.connect(cameraView.insertKey)

        camToggle = QAction('&Toggle camera control', self)
        camToggle.setShortcuts(QKeySequence(Qt.Key_T))
        camToggle.setShortcutContext(Qt.ApplicationShortcut)
        camToggle.triggered.connect(cameraView.toggle)

        camCopAnim = QAction('Snap came&ra to animation', self)
        camCopAnim.setShortcuts(QKeySequence(Qt.Key_R))
        camCopAnim.setShortcutContext(Qt.ApplicationShortcut)
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
        fs.setShortcut(Qt.Key_F11)
        fs.setShortcutContext(Qt.ApplicationShortcut)
        fs.triggered.connect(self.__fullScreenViewport)

        self.__previewMenu = toolsMenu.addMenu('Preview resolution')
        previewRadioGroup = QActionGroup(self)
        # add action & connect it to the setPreviewRes with right parameters
        hd = self.__previewMenu.addAction('1070p (HD)')
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
            option = {1.0: viewport, 0.5: half, 0.25: quart, 0.125: eight}[float(gSettings.value('GLViewScale'))]
        option.setChecked(True)

        self.__menuBar.addMenu(self.__dockWidgetMenu)
        self.__menuBar.addAction('About').triggered.connect(self.__aboutDialog)
        self.__restoreUiLock(lock)

    def _addDockWidget(self, widget, name=None, where=Qt.RightDockWidgetArea, direction=Qt.Horizontal):
        dockWidget = super(App, self)._addDockWidget(widget, name, where, direction)
        self.__dockWidgetMenu.addAction(dockWidget.toggleViewAction())
        return dockWidget

    def __record(self):
        diag = QDialog()
        fId = gSettings.value('RecordFPS', 2)
        rId = gSettings.value('RecordResolution', 3)
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
        diag.exec_()
        if diag.result() != QDialog.Accepted:
            return
        gSettings.setValue('RecordFPS', fps.currentIndex())
        gSettings.setValue('RecordResolution', resolution.currentIndex())

        FPS = int(fps.currentText())
        HEIGHT = int(resolution.currentText())
        WIDTH = (HEIGHT * 16) / 9
        data = (ctypes.c_ubyte * (WIDTH * HEIGHT * 3))()  # alloc buffer once
        flooredStart = self._timer.secondsToBeats(int(self._timer.beatsToSeconds(self._timer.start) * FPS) / float(FPS))
        duration = self._timer.beatsToSeconds(self._timer.end - flooredStart)
        if not fileutil.exists('capture'):
            os.makedirs('capture')
        progress = QProgressDialog(self)
        progress.setMaximum(int(duration * FPS))
        prevFrame = 0
        for frame in xrange(int(duration * FPS)):
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
            sceneFile = os.path.join(ScenesPath(), shot.sceneName + SCENE_EXT)
            scene = Scene.getScene(sceneFile)
            scene.setSize(WIDTH, HEIGHT)

            uniforms = self.__shotsManager.evaluate(beats)
            textureUniforms = self.__shotsManager.additionalTextures(beats)
            self.__sceneView._cameraInput.setData(*(uniforms['uOrigin'] + uniforms['uAngles']))  # feed animation into camera so animationprocessor can read it again
            cameraData = self.__sceneView._cameraInput.data()

            modifier = os.path.join(ProjectDir(), 'animationprocessor.py')
            if fileutil.exists(modifier):
                execfile(modifier, globals(), locals())

            for name in self.__sceneView._textures:
                uniforms[name] = self.__sceneView._textures[name]._id

            scene.drawToScreen(self._timer.beatsToSeconds(beats), beats, uniforms, (0, 0, WIDTH, HEIGHT), textureUniforms)
            scene.colorBuffers[-1][0].use()

            from OpenGL.GL import glGetTexImage, GL_TEXTURE_2D, GL_RGB, GL_UNSIGNED_BYTE
            glGetTexImage(GL_TEXTURE_2D, 0, GL_RGB, GL_UNSIGNED_BYTE, data)

            QImage(data, WIDTH, HEIGHT, QImage.Format_RGB888).mirrored(False, True).save('capture/dump_%s_%05d.jpg' % (FPS, int(self._timer.beatsToSeconds(self._timer.start) * FPS) + frame))
        progress.close()

        if not fileutil.exists('convertcapture'):
            os.makedirs('convertcapture')
        with fileutil.edit('convertcapture/convert.bat') as fh:
            start = ''
            start2 = ''
            if int(self._timer.start * FPS) > 0:
                start = '-start_number {} '.format(int(self._timer.beatsToSeconds(self._timer.start) * FPS))
                start2 = '-vframes {} '.format(int(self._timer.beatsToSeconds(self._timer.start) * FPS))
            fh.write('cd "../capture"\n"../convertcapture/ffmpeg.exe" -framerate {} {}-i dump_{}_%%05d.jpg {}-c:v libx264 -r {} -pix_fmt yuv420p "../convertcapture/output.mp4"'.format(FPS, start, FPS,
                                                                                                                                                                                        start2, FPS))

        with fileutil.edit('convertcapture/convertGif.bat') as fh:
            start = ''
            start2 = ''
            if int(self._timer.start * FPS) > 0:
                start = '-start_number {} '.format(int(self._timer.beatsToSeconds(self._timer.start) * FPS))
                start2 = '-vframes {} '.format(int(self._timer.beatsToSeconds(self._timer.start) * FPS))
            fh.write('cd "../capture"\n"../convertcapture/ffmpeg.exe" -framerate {} {}-i dump_{}_%%05d.jpg {}-r {} "../convertcapture/output.gif"'.format(FPS, start, FPS, start2, FPS))

        sound = self.timeSlider.soundtrackPath()
        if not sound:
            return
        with fileutil.edit('convertcapture/merge.bat') as fh:
            startSeconds = self._timer.beatsToSeconds(self._timer.start)
            fh.write('ffmpeg -i output.mp4 -itsoffset {} -i "{}" -vcodec copy -shortest merged.mp4'.format(-startSeconds, sound))

    def __restoreUiLock(self, action):
        state = True if gSettings.value('lockui', '0') == '1' else False
        action.setChecked(state)
        features = QDockWidget.NoDockWidgetFeatures if state else QDockWidget.AllDockWidgetFeatures
        for dockWidget in self.findChildren(QDockWidget):
            dockWidget.setFeatures(features)

    def __fullScreenViewport(self, *args):
        # force floating
        dockWidget = self.__sceneView.parent()
        if not dockWidget.isFloating():
            dockWidget.setFloating(True)
        if dockWidget.isFullScreen():
            dockWidget.showNormal()
            dockWidget.resize(self.__restoreFullScreenSize)
        else:
            self.__restoreFullScreenSize = dockWidget.size()
            dockWidget.showFullScreen()

    def __toggleUILock(self, state):
        gSettings.setValue('lockui', '1' if state else '0')
        features = QDockWidget.NoDockWidgetFeatures if state else QDockWidget.AllDockWidgetFeatures
        for dockWidget in self.findChildren(QDockWidget):
            # only affect docked widgets
            if not dockWidget.isFloating():
                dockWidget.setFeatures(features)

    def __onViewShot(self, start, end):
        self._timer.start = start
        self._timer.end = end - 0.01

    def __aboutDialog(self):
        QMessageBox.about(self, 'About SqrMelon',
                          r"""<p>SqrMelon is a tool to manage a versions (scenes) of a graph of fragment shaders (templates) & drive uniforms with animation curves (shots).</p>
                          <p>Download or find documentation on <a href="https://github.com/trevorvanhoof/sqrmelon/">GitHub/</a>!</p>
                          <p>Icons from <a href="https://icons8.com/">icons8.com/</a></p>""")

    def __colorPicker(self):
        color = QColorDialog.getColor()
        color = "vec3(" + str(round(color.red() / 255.0, 2)) + ", " + str(round(color.green() / 255.0, 2)) + ", " + str(round(color.blue() / 255.0, 2)) + ")"
        cb = QApplication.clipboard()
        cb.setText(color, mode=cb.Clipboard)

    def __onCtrlS(self):
        if qApp.focusWidget() != self.__sceneView:
            self.saveProject()
        else:
            self.__sceneView.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_S, Qt.ControlModifier))

    def saveProject(self):
        self.__sceneView.saveCameraData()
        self.__shotsManager.saveAllShots()
        self._timer.saveState()
        QMessageBox.information(self, 'Save succesful!', 'Animation, shot & timing changes have been saved.')

    def closeEvent(self, event):
        res = QMessageBox.question(self, 'Save before exit?', 'Do you want to save?', QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        if res == QMessageBox.Cancel:
            event.ignore()
            return
        if res == QMessageBox.Yes:
            self.saveProject()
        super(App, self).hideEvent(event)

    def __setCurrentShot(self, *args):
        shot = self.__shotsManager.shotAtTime(self._timer.time)
        if shot is None:
            self.__sceneView.setScene(None)
            self.__profiler.setScene(None)
            return
        sceneFile = os.path.join(ScenesPath(), shot.sceneName + SCENE_EXT)
        sc = Scene.getScene(sceneFile)
        self.__sceneView.setScene(sc)
        self.__profiler.setScene(sc)

    def __openProject(self, path):
        gSettings.setValue('currentproject', path)
        self.__sceneList.projectOpened()
        self.__shotsManager.projectOpened()
        self._timer.projectOpened()

    def __initializeProject(self):
        if gSettings.contains('currentproject'):
            project = str(gSettings.value('currentproject'))
            if fileutil.exists(project):
                self.__openProject(project)
                return
        project = [x for x in list(os.listdir(os.getcwd())) if x.endswith(PROJ_EXT)]
        if project:
            self.__openProject(os.path.join(os.getcwd(), project[0]))
            return

    def __onNewProject(self):
        if gSettings.contains('currentproject') and QMessageBox.warning(self, 'Creating new project',
                                                                        'Any unsaved changes will be lost. Continue?',
                                                                        QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
            return

        currentPath = os.getcwd()
        if gSettings.contains('currentproject'):
            project = str(gSettings.value('currentproject'))
            if fileutil.exists(project):
                currentPath = os.path.dirname(project)

        res = QFileDialog.getSaveFileName(self, 'Create new project', currentPath, 'Project folder')
        if not res:
            return
        shutil.copytree(DEFAULT_PROJECT, res, ignore=lambda p, f: [] if os.path.basename(p).lower() == 'Scenes' else [n for n in f if os.path.splitext(n)[-1].lower() in IGNORED_EXTENSIONS])
        projectFile = os.path.join(res, os.path.basename(res) + PROJ_EXT)
        fileutil.create(projectFile)
        self.__openProject(projectFile)

    def __onOpenProject(self):
        if gSettings.contains('currentproject') and QMessageBox.warning(self, 'Changing project',
                                                                        'Any unsaved changes will be lost. Continue?',
                                                                        QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
            return

        currentPath = os.getcwd()
        if gSettings.contains('currentproject'):
            project = str(gSettings.value('currentproject'))
            if fileutil.exists(project):
                currentPath = os.path.dirname(project)

        res = QFileDialog.getOpenFileName(self, 'Open project', currentPath, 'Project files (*%s)' % PROJ_EXT)
        if not res:
            return
        self.__openProject(res)


def run():
    app = QApplication(sys.argv)
    win = App()
    win.show()
    app.exec_()


if __name__ == '__main__':
    # import profileutil
    # profileutil.runctx('run()', globals(), locals(), executable=profileutil.QCACHEGRIND)
    try:
        run()
    except Exception as e:
        QMessageBox.critical(None, 'Unhandled exception', traceback.format_exc(e))
