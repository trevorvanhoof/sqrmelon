import functools
import time
from math import degrees, radians
from typing import Any, cast, Iterable, Optional, Union

import icons
from animationgraph.curveview import CurveEditor
from mathutil import addVec3, multVec3, rotateVec3
from qt import *
from qtutil import DoubleSpinBox, hlayout
from scene import CameraTransform
from shots import ShotManager
from timeslider import Timer
import json

Float6 = tuple[float, float, float, float, float, float]


class Camera(QWidget):
    """
    Input that shows editable camera position and angles (degrees).
    Additionally contains event handlers for 3D flying keyboard & mouse input.
    """
    MOVE_SPEEDS = (0.5, 5.0, 30.0)
    TURN_SPEEDS = (0.2, 0.8, 3.0)
    MOUSE_SPEED = 3.0

    MOVE_LUT = {Qt.Key.Key_A: (-1.0, 0.0, 0.0),
                Qt.Key.Key_D: (1.0, 0.0, 0.0),
                Qt.Key.Key_Q: (0.0, 1.0, 0.0),
                Qt.Key.Key_E: (0.0, -1.0, 0.0),
                Qt.Key.Key_S: (0.0, 0.0, -1.0),
                Qt.Key.Key_W: (0.0, 0.0, 1.0)}

    TURN_LUT = {Qt.Key.Key_Up: (1.0, 0.0, 0.0),
                Qt.Key.Key_Down: (-1.0, 0.0, 0.0),
                Qt.Key.Key_Left: (0.0, -1.0, 0.0),
                Qt.Key.Key_Right: (0.0, 1.0, 0.0),
                Qt.Key.Key_Home: (0.0, 0.0, -1.0),
                Qt.Key.Key_End: (0.0, 0.0, 1.0)}

    cameraChanged = Signal()

    def __init__(self, animator: ShotManager, animationEditor: CurveEditor, timer: Timer):
        super(Camera, self).__init__()
        layout = QGridLayout()
        self.setLayout(layout)

        for i, value in enumerate([ 4, 8, 8, 8, 1, 1, 1 ]):
            layout.setColumnStretch(i, value)
        for i, value in enumerate([ 1, 1, 1, 1, 9999 ]):
            layout.setRowStretch(i, value)
        layout.addItem(QSpacerItem(1, 1, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding), 4, 0)

        self.__enabled = QPushButton('')
        self.__enabled.clicked.connect(self.toggle)
        self.__enabled.setFlat(True)
        self.__enabled.setStyleSheet("QPushButton { border-style: none; border-width: 0px; padding: 0px; }")
        layout.addWidget(QLabel("Animate"), 0, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.__enabled, 0, 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignCenter)

        self.__cameraControlActive = True  # the toggle call will make this the opposite
        self.toggle()
        self.__enabled.setIconSize(QSize(20, 20))

        timer.timeChanged.connect(self.__copyAnim)
        copyAnim = QPushButton(QIcon(icons.get('Film-Refresh-48')), '')
        copyAnim.setToolTip('Copy animation to camera.')
        self.__animator = animator
        self.__animationEditor = animationEditor
        self._timer = timer
        copyAnim.clicked.connect(self.copyAnim)
        layout.addWidget(copyAnim, 0, 6, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignCenter)
        copyAnim.setIconSize(QSize(20, 20))

        self.__keyStates: dict[Qt.Key, bool] = {Qt.Key.Key_Shift: False, Qt.Key.Key_Control: False}
        for key in Camera.MOVE_LUT:
            self.__keyStates[key] = False
        for key in Camera.TURN_LUT:
            self.__keyStates[key] = False
        self.__data = CameraTransform()
        self.__inputs = []

        cameraTransformViewData = [ [ "Translate", 1 ], [ "Rotate", 5 ] ]
        for i, value in enumerate(self.__data):
            cameraTransformViewDataBaseIdx = 0 if (i < 3) else 1
            self.layout().addWidget(QLabel(cameraTransformViewData[cameraTransformViewDataBaseIdx][0]), cameraTransformViewDataBaseIdx + 1, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignCenter)

            s = DoubleSpinBox(value)
            s.setMinimumWidth(75)
            s.setDecimals(3)
            s.setSingleStep(cameraTransformViewData[cameraTransformViewDataBaseIdx][1])
            s.valueChanged.connect(functools.partial(self.__setData, i))
            layout.addWidget(s, cameraTransformViewDataBaseIdx + 1, 1 + (i % 3))
            self.__inputs.append(s)

        iconizedPushButtonsData = [
            [ 1, 4, 'Copy-48', 'Copy camera translation to clipboard.', self.__onCopyCameraPos ],
            [ 1, 5, 'Paste-48', 'Paste camera translation from clipboard.', self.__onPasteCameraPos ],
            [ 1, 6, 'Reset-48', 'Reset camera translation.', self.__onResetCameraPos ],
            [ 2, 4, 'Copy-48', 'Copy camera rotation to clipboard.', self.__onCopyCameraRot ],
            [ 2, 5, 'Paste-48', 'Paste camera rotation from clipboard.', self.__onPasteCameraRot ],
            [ 2, 6, 'Reset-48', 'Reset camera rotation.', self.__onResetCameraRot ],
            [ 3, 4, 'Copy-48', 'Copy camera transform to clipboard.', self.__onCopyCameraTxx ],
            [ 3, 5, 'Paste-48', 'Paste camera transform from clipboard.', self.__onPasteCameraTxx ],
            [ 3, 6, 'Reset-48', 'Reset camera transform.', self.__onResetCameraTxx ],
        ]
        for value in iconizedPushButtonsData:
            s = QPushButton(QIcon(icons.get(value[2])), '')
            s.setToolTip(value[3])
            s.setIconSize(QSize(20, 20))
            s.clicked.connect(value[4])
            layout.addWidget(s, value[0], value[1], Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignCenter)

        self.__prevTime: Optional[float] = None
        self.__appLoop = QTimer()
        self.__appLoop.timeout.connect(self.flyUpdate)
        self.__appLoop.start(1000 // 60)
        self.__drag: Optional[tuple[QPoint, tuple[float, float, float]]] = None
        self.__dirty = False

    def insertKey(self) -> None:
        """Insert a key into the default camera channels with the current timeslider time and current camera transform."""
        channels = 'uOrigin.x', 'uOrigin.y', 'uOrigin.z', 'uAngles.x', 'uAngles.y', 'uAngles.z'
        self.__animationEditor.setKey(channels, tuple(self.__data[:]))  # type: ignore

    def forwardPositionKey(self) -> None:
        """Insert a key into the selected channels with the current timeslider time and current camera position."""
        self.__animationEditor.setTransformKey(self.__data.translate)

    def forwardRotationKey(self) -> None:
        """Insert a key into the selected channels with the current timeslider time and current camera rotation."""
        self.__animationEditor.setTransformKey(self.__data.rotate)

    def __copyAnim(self, *_: Any) -> None:
        if not self.__cameraControlActive:
            self.copyAnim()

    def copyAnim(self) -> None:
        """Snap the camera transform to the currently animated camera position."""
        data = self.__animator.evaluate(self._timer.time)
        if 'uOrigin' not in data or 'uAngles' not in data:
            return
        uOrigin = data['uOrigin']
        uAngles = data['uAngles']
        assert isinstance(uOrigin, list)
        assert isinstance(uAngles, list)
        self.__data = CameraTransform(*(uOrigin + uAngles))
        for spinBox, value in zip(self.__inputs, self.__data.data):
            tmp = spinBox.blockSignals(True)
            spinBox.setValue(value)
            spinBox.blockSignals(tmp)
        self.cameraChanged.emit()

    def toggle(self, *_: Any) -> None:
        """Toggle making the camera follow the animated values or staying in the user's hands while playing back or scrubbing the timeline."""
        self.__cameraControlActive = not self.__cameraControlActive
        if self.__cameraControlActive:
            self.__enabled.setIcon(icons.get('Toggle Off-48'))
            self.__enabled.setToolTip('Enable camera animation.')
        else:
            self.__enabled.setIcon(icons.get('Toggle On-48'))
            self.__enabled.setToolTip('Disable camera animation.')

    def __setData(self, index: int, value: float) -> None:
        """Called from the UI, performing unit conversion on angles."""
        if index in (3, 4, 5):
            value = radians(value)
        self.__data[index] = value
        self.cameraChanged.emit()

    def data(self) -> CameraTransform:
        return self.__data

    def setData(self, *args: float) -> None:
        self.__data = CameraTransform(*args)

    def releaseAll(self) -> None:
        for key in self.__keyStates:
            self.__keyStates[key] = False
        self.__drag = None

    def camera(self) -> CameraTransform:
        return self.__data

    def flyMouseStart(self, event: QMouseEvent) -> None:
        self.__drag = event.pos(), self.__data.rotate

    def flyMouseUpdate(self, event: QMouseEvent, size: QSize) -> None:
        if self.__drag is None:
            return
        delta = event.pos() - self.__drag[0]
        scale = (size.width() + size.height()) * 0.5
        ry = (delta.x() / scale) * Camera.MOUSE_SPEED
        rx = (delta.y() / scale) * Camera.MOUSE_SPEED
        if rx or ry:
            self.__data.rotate = (self.__drag[1][0] - rx,
                                  self.__drag[1][1] + ry,
                                  self.__data.rotate[2])
            self.__dirty = True

    def flyMouseEnd(self, _: Any) -> None:
        self.__drag = None

    def flyKeyboardInput(self, keyEvent: QKeyEvent, state: bool) -> None:
        if keyEvent.key() in self.__keyStates:
            self.__keyStates[Qt.Key(keyEvent.key())] = state

    def flyUpdate(self) -> None:
        if self.__prevTime is None:
            self.__prevTime = time.time()
            return
        deltaTime = time.time() - self.__prevTime
        self.__prevTime = time.time()

        # track whether a key was pressed
        dirtyTranslate = False
        dirtyRotate = False

        speedId = 1 - int(self.__keyStates[Qt.Key.Key_Control]) + int(self.__keyStates[Qt.Key.Key_Shift])

        # compute move vector
        translate = (0.0, 0.0, 0.0)
        for key in Camera.MOVE_LUT:
            if not self.__keyStates[key]:
                continue
            dirtyTranslate = True
            translate = addVec3(translate, Camera.MOVE_LUT[key])

        # compute rotate angles
        for key in Camera.TURN_LUT:
            if not self.__keyStates[key]:
                continue
            dirtyRotate = True
            rotate = multVec3(Camera.TURN_LUT[key], deltaTime * Camera.TURN_SPEEDS[speedId])
            if rotate[0] or rotate[1] or rotate[2]:
                self.__data.rotate = addVec3(self.__data.rotate, rotate)

        # if no keys were pressed, we're done
        dirty = dirtyTranslate | dirtyRotate | self.__dirty
        self.__dirty = False
        if not dirty:
            return

        if dirtyTranslate:
            translate = multVec3(translate, deltaTime * Camera.MOVE_SPEEDS[speedId])
            self.__data.translate = addVec3(self.__data.translate, rotateVec3(translate, self.__data.rotate[:2]))

        for i in range(len(self.__data)):
            value = self.__data[i]
            if i in (3, 4, 5):
                value = degrees(value)
            self.__inputs[i].setValueSilent(value)
        self.cameraChanged.emit()

    def __onCopyCameraPos(self):
        QApplication.clipboard().setText(json.dumps(self.__data.data[:3]))

    def __onPasteCameraPos(self):
        try:
            cpText = json.loads(QApplication.clipboard().text())
            self.__data.translate = cpText
            if len(cpText) == 3:
                for i, value in enumerate(cpText):
                    self.__inputs[i].setValueSilent(value)
                self.cameraChanged.emit()

        except:
            return

    def __onResetCameraPos(self):
        for i in range(0, 3):
            self.__inputs[i].setValueSilent(0)
        self.__data.translate = [ 0, 0, 0 ]
        self.cameraChanged.emit()

    def __onCopyCameraRot(self):
        rot = self.__data.data[3:6]
        for i, value in enumerate(rot):
            rot[i] = degrees(value)
        QApplication.clipboard().setText(json.dumps(rot))

    def __onPasteCameraRot(self):
        try:
            cpText = json.loads(QApplication.clipboard().text())
            if len(cpText) == 3:
                for i in range(len(cpText)):
                    self.__inputs[i + 3].setValueSilent(cpText[i])
                self.__data.rotate = [ radians(cpText[0]), radians(cpText[1]), radians(cpText[2]) ]
                self.cameraChanged.emit()

        except:
            return

    def __onResetCameraRot(self):
        for i in (3, 4, 5):
            self.__inputs[i].setValueSilent(0)
            self.__data.rotate = [ 0, 0, 0 ]
        self.cameraChanged.emit()

    def __onCopyCameraTxx(self):
        txx = self.__data.data
        for i in range(3, 6):
            txx[i] = degrees(txx[i])
        QApplication.clipboard().setText(json.dumps(txx))

    def __onPasteCameraTxx(self):
        try:
            cpText = json.loads(QApplication.clipboard().text())
            if len(cpText) == 6:
                for i in range(len(cpText)):
                    self.__inputs[i].setValueSilent(cpText[i])
                self.__data.translate = cpText[:3]
                self.__data.rotate = [ radians(cpText[3]), radians(cpText[4]), radians(cpText[5]) ]
                self.cameraChanged.emit()

        except:
            return

    def __onResetCameraTxx(self):
        self.__onResetCameraPos()
        self.__onResetCameraRot()
