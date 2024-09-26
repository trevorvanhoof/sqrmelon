from __future__ import annotations
from math import radians
from flex_project.widgets.qt import *
from flex_project.utils.mmath import Mat44, Vec4

Float3 = tuple[float, float, float]
Float6 = tuple[float, float, float, float, float, float]


class CameraEdit(QWidget):
    """The edit owns the camera.

    An animator can drive the camera while playing
    if sync is on, by simply setting the editor values.

    If sync is off, the editor remains unaltered.
    """
    changed = Signal(tuple)

    def __init__(self) -> None:
        super().__init__()

        # The GUI
        g = QGridLayout()
        self.setLayout(g)
        self.__edits = []

        # Sync toggle
        b = QPushButton()
        b.setCheckable(True)
        b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        g.addWidget(b, 0, 0, 2, 1)

        for y in range(2):
            # Labels
            labels = 'translate', 'rotate'
            g.addWidget(QLabel(labels[y]), y, 1)

            # Edits
            for x in range(3):
                edit = DoubleEdit()
                self.__edits.append(edit)
                edit.valueChanged.connect(self.__emitChanged)
                g.addWidget(edit, y, x + 2)

                # Rotate widgets have a larger step size
                if y == 1:
                    edit.setSingleStep(5)

                # Set a background gradient based on the axis
                colors = '255, 0, 0', '0, 255, 0', '0, 0, 255'
                edit.lineEdit().setStyleSheet(f'background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgba({colors[x]}, 200), stop:0.15 rgba({colors[x]}, 60), stop:1 rgba({colors[x]}, 0))')

        # Key states
        self.__keyboard: dict[Qt.Key, bool] = {}

        # Coroutine
        self.__coroutine = QTimer()
        self.__coroutine.timeout.connect(self.__tick)
        self.__coroutine.start(1000 // 60)

    @property
    def translate(self) -> Float3:
        return tuple(self.__edits[i].value() for i in range(3))  # type: ignore

    @translate.setter
    def translate(self, value: Float3) -> None:
        tmp = self.blockSignals(True)
        for i, v in enumerate(value):
            self.__edits[i].setValue(v)
        self.blockSignals(tmp)
        self.__emitChanged()

    @property
    def degrees(self) -> Float3:
        return tuple(self.__edits[i].value() for i in range(3))  # type: ignore

    @degrees.setter
    def degrees(self, value: Float3) -> None:
        tmp = self.blockSignals(True)
        for i, v in enumerate(value):
            self.__edits[i + 3].setValue(v)
        self.blockSignals(tmp)
        self.__emitChanged()

    @property
    def state(self) -> Float6:
        return tuple(self.__edits[i].value() for i in range(6))  # type: ignore

    @state.setter
    def state(self, value: Float6) -> None:
        tmp = self.blockSignals(True)
        for i, v in enumerate(value):
            self.__edits[i].setValue(v)
        self.blockSignals(tmp)
        self.__emitChanged()

    def __emitChanged(self, *_) -> None:
        self.changed.emit(self.state)

    def flyKey(self, event: QKeyEvent) -> None:
        self.__keyboard[event.key()] = event.type() == QEvent.Type.KeyPress

    def cameraMatrix(self) -> Mat44:
        state = self.translate + tuple(radians(degrees) for degrees in self.degrees)
        return Mat44.TRS(*state)

    def __keyboardAxis(self, positive: Qt.Key, negative: Qt.Key) -> int:
        axis = int(self.__keyboard.get(positive, False))
        axis -= 2 * int(self.__keyboard.get(negative, False))
        return axis

    def __tick(self) -> None:
        shift = self.__keyboard.get(Qt.Key.Key_Shift)
        control = self.__keyboard.get(Qt.Key.Key_Control)
        delta = 1000.0 / 60.0
        if shift:
            delta *= 10.0
        if control:
            delta *= 0.1

        rotateSpeed = 90.0 * delta
        rx = self.__keyboardAxis(Qt.Key.Key_Left, Qt.Key.Key_Right) * rotateSpeed
        ry = self.__keyboardAxis(Qt.Key.Key_Home, Qt.Key.Key_End) * rotateSpeed
        rz = self.__keyboardAxis(Qt.Key.Key_Up, Qt.Key.Key_Down) * rotateSpeed
        degrees = self.degrees
        degrees = degrees[0] + rx, degrees[1] + ry, degrees[2] + rz
        self.degrees = degrees

        moveSpeed = 10.0 * delta
        tx = self.__keyboardAxis(Qt.Key.Key_A, Qt.Key.Key_D) * moveSpeed
        ty = self.__keyboardAxis(Qt.Key.Key_Q, Qt.Key.Key_E) * moveSpeed
        tz = self.__keyboardAxis(Qt.Key.Key_W, Qt.Key.Key_S) * moveSpeed
        t = self.cameraMatrix() * Vec4(tx, ty, tz, 0.0)
        translate = self.translate
        translate = translate[0] + t[0], translate[1] + t[1], translate[2] + t[2]
        self.translate = translate
