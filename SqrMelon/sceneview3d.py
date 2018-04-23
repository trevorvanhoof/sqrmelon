from qtutil import *
import time
import os
from overlays import loadImage
from util import gSettings, ProjectDir
from scene import Scene
from OpenGL.GL import glEnable, glDisable, glBlendFunc, glDepthFunc, GL_LEQUAL, GL_DEPTH_TEST, GL_BLEND, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA

_noSignalImage = None


class SceneView(QGLWidget):
    """
    OpenGL 3D viewport.

    Core functionalities are that it is aware of the camera sequencer and timeline,
    so it can decide what camera to evaluate & extract animation data for this frame.

    This is done implicitly in paintGL.

    It wraps a single Scene() instance, which is set from outside and intended
    to match the scene used by the current shot. When a valid scene is set,
    it is rendered to the viewport on every repaint.

    Last it can be connected to a camera widget (setCamera) to which it fill
    forward left mouse drag and keyboard input (WASDQE).
    """

    def __init__(self, shotManager, timer, overlays=None):
        """
        :type overlays: Overlays
        """
        super(SceneView, self).__init__()

        self._timer = timer
        self._animator = shotManager
        self.__overlays = overlays
        self._scene = None
        self._size = 1, 1
        self._previewRes = None, None, 1.0
        if gSettings.contains('GLViewScale'):
            self._previewRes = None, None, float(gSettings.value('GLViewScale'))
        self._cameraInput = None
        self.setFocusPolicy(Qt.StrongFocus)
        self._textures = {}
        self._prevTime = time.time()

    def setPreviewRes(self, widthOverride, heightOverride, scale):
        if widthOverride is not None:
            x = self.parent().width() - self.width()
            y = self.parent().height() - self.height()
            self.parent().setGeometry(self.parent().x(), self.parent().y(), widthOverride + x, heightOverride + y)
        self._previewRes = widthOverride, heightOverride, scale
        gSettings.setValue('GLViewScale', scale)
        self.__onResize()

    @property
    def _cameraData(self):
        return self._cameraInput.data()

    def setCamera(self, cameraInput):
        """
        :type cameraInput: camera.Camera
        """
        self._cameraInput = cameraInput
        if self._scene:
            # copy the scene camera data to the camera input, so each scene can store it's own user-camera
            self._cameraInput.setCamera(self._scene.readCameraData())

    def saveCameraData(self):
        if self._cameraInput and self._scene:
            # back up user camera position in scene data
            self._scene.setCameraData(self._cameraInput.camera())

    def setScene(self, scene):
        """
        :type scene: scene.Scene
        """
        if scene == self._scene:
            self.repaint()
            return

        if self._cameraInput:
            # back up user camera position in scene data
            self.saveCameraData()
            if scene is not None:
                # copy the scene camera data to the camera input, so each scene can store it's own user-camera
                self._cameraInput.setCamera(scene.readCameraData())

        # update which scene's files we are watching for updates
        if self._scene:
            try:
                self._scene.fileSystemWatcher.fileChanged.disconnect(self.repaint)
            except:
                pass

        if scene:
            scene.fileSystemWatcher.fileChanged.connect(self.repaint)

        # resize color buffers used by scene
        self._scene = scene
        if scene is not None:
            self._scene.setSize(*self._size)

        self.repaint()

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        # glDepthMask(GL_TRUE)

        IMAGE_EXTENSIONS = '.png', '.bmp', '.tga'
        textureFolder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Textures')
        if os.path.exists(textureFolder):
            for texture in os.listdir(textureFolder):
                fname, ext = os.path.splitext(texture)
                if ext.lower() in IMAGE_EXTENSIONS:
                    self._textures[fname] = loadImage(os.path.join(textureFolder, texture))

        self._prevTime = time.time()
        self._timer.kick()

    def calculateAspect(self, w, h):
        aspectH = w / 16 * 9
        aspectW = h / 9 * 16

        newW = w
        if (aspectH > h):
            aspectH = h
            newW = aspectW

        return newW, aspectH

    def paintGL(self):
        newTime = time.time()
        deltaTime = newTime - self._prevTime

        # work around double repaint events collecting in the queue
        if deltaTime == 0.0:
            return

        self._prevTime = newTime

        width, height = self.calculateAspect(self.width(), self.height())
        viewport = (int((self.width() - width) * 0.5),
                    int((self.height() - height) * 0.5),
                    width,
                    height)

        if self._scene:
            uniforms = self._animator.evaluate(self._timer.time)
            textureUniforms = self._animator.additionalTextures(self._timer.time)

            cameraData = self._cameraData
            scene = self._scene
            modifier = os.path.join(ProjectDir(), 'animationprocessor.py')
            if os.path.exists(modifier):
                beats = self._timer.time
                execfile(modifier, globals(), locals())

            for name in self._textures:
                uniforms[name] = self._textures[name]._id

            self._scene.drawToScreen(self._timer.beatsToSeconds(self._timer.time), self._timer.time, uniforms, viewport, additionalTextureUniforms=textureUniforms)

        else:
            # no scene active, time cursor outside any enabled shots?
            global _noSignalImage
            if _noSignalImage is None:
                _noSignalImage = loadImage(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icons/nosignal.png'))
            glDisable(GL_DEPTH_TEST)
            if _noSignalImage:
                glEnable(GL_BLEND)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                Scene.drawColorBufferToScreen(_noSignalImage, viewport)
                glDisable(GL_BLEND)

        if self.__overlays:
            image = self.__overlays.colorBuffer()
            if image:
                color = (self.__overlays.overlayColor().red() / 255.0,
                         self.__overlays.overlayColor().green() / 255.0,
                         self.__overlays.overlayColor().blue() / 255.0,
                         self.__overlays.overlayColor().alpha() / 255.0)
                glDisable(GL_DEPTH_TEST)
                glEnable(GL_BLEND)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                Scene.drawColorBufferToScreen(image, viewport, color)
                glDisable(GL_BLEND)

    def __onResize(self):
        w = self.width()
        h = self.height()
        if self._previewRes[0]:
            w = self._previewRes[0]
        if self._previewRes[1]:
            h = self._previewRes[1]
        w = int(w * self._previewRes[2])
        h = int(h * self._previewRes[2])
        self._size = self.calculateAspect(w, h)[0:2]
        if self._scene:
            self._scene.setSize(*self._size)
        self.repaint()

    def resizeGL(self, w, h):
        self.__onResize()

    def keyPressEvent(self, keyEvent):
        super(SceneView, self).keyPressEvent(keyEvent)
        if self._cameraInput:
            self._cameraInput.flyKeyboardInput(keyEvent, True)

    def keyReleaseEvent(self, keyEvent):
        super(SceneView, self).keyReleaseEvent(keyEvent)
        if self._cameraInput:
            self._cameraInput.flyKeyboardInput(keyEvent, False)

    def mousePressEvent(self, mouseEvent):
        super(SceneView, self).mousePressEvent(mouseEvent)
        if self._cameraInput:
            self._cameraInput.flyMouseStart(mouseEvent)

    def mouseMoveEvent(self, mouseEvent):
        super(SceneView, self).mouseMoveEvent(mouseEvent)
        if self._cameraInput:
            self._cameraInput.flyMouseUpdate(mouseEvent, self.size())

    def mouseReleaseEvent(self, mouseEvent):
        super(SceneView, self).mouseReleaseEvent(mouseEvent)
        if self._cameraInput:
            self._cameraInput.flyMouseEnd(mouseEvent)
