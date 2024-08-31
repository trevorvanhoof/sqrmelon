"""
Imports QT with the right version settings
Exposes a bunch of useful subclasses and utility functions.
"""
from typing import Any, cast, Optional

from qt import *

# TODO: floating dockwidget splitter state does not seem to be saved correctly

class QMainWindowState(QMainWindow):
    """A MainWindow that remembers its position and dock widget states."""

    def __init__(self, settings: QSettings) -> None:
        super(QMainWindowState, self).__init__()
        self.settings = settings
        self.setObjectName(self.__class__.__name__)

    def _store(self) -> None:
        self.settings.setValue('%s/geometry' % self.__class__.__name__, self.saveGeometry())
        self.settings.setValue('%s/state' % self.__class__.__name__, self.saveState())

    def _restore(self) -> None:
        r = self.settings.value('%s/geometry' % self.__class__.__name__, None)
        if r is not None:
            self.restoreGeometry(r)  # type: ignore
        s = self.settings.value('%s/state' % self.__class__.__name__, None)
        if s is not None:
            self.restoreState(s)  # type: ignore

    def showEvent(self, event: QShowEvent) -> None:
        self._restore()

    def hideEvent(self, event: QHideEvent) -> None:
        self._store()

    def _addDockWidget(self,
                       widget: QWidget,
                       name: Optional[str] = None,
                       where: Qt.DockWidgetArea = Qt.DockWidgetArea.RightDockWidgetArea,
                       direction: Qt.Orientation = Qt.Orientation.Horizontal) -> QDockWidget:
        name = name or widget.__class__.__name__
        dock = QDockWidget(self)
        dock.setWidget(widget)
        dock.setObjectName(name)
        dock.setWindowTitle(name)
        self.addDockWidget(where, dock, direction)
        return dock


class QSplitterState(QSplitter):
    """
    A draggable layout that remembers its state.
    """

    def __init__(self, splitterName: str, orientation: Qt.Orientation) -> None:
        super(QSplitterState, self).__init__(orientation)
        self.setObjectName(splitterName)

    def _store(self) -> None:
        window = self.window()
        while window.parent():
            window = window.parent().window()  # type: ignore
        if hasattr(window, 'settings'):
            window.settings.setValue('%s/state' % self.objectName(), self.saveState())

    def _restore(self) -> None:
        window = self.window()
        while window.parent():
            window = window.parent().window()  # type: ignore
        if hasattr(window, 'settings'):
            state = window.settings.value('%s/state' % self.objectName())
            if state:
                self.restoreState(state)

    def showEvent(self, event: QShowEvent) -> None:
        self._restore()

    def hideEvent(self, event: QHideEvent) -> None:
        self._store()


def hlayout(spacing: int = 0, margin: int = 0) -> QHBoxLayout:
    """Qt layout constructor wrapped to have no spacing and padding by default."""
    layout = QHBoxLayout()
    layout.setContentsMargins(margin, margin, margin, margin)
    layout.setSpacing(spacing)
    layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    return layout


def vlayout(spacing: int = 0, margin: int = 0) -> QVBoxLayout:
    """Qt layout constructor wrapped to have no spacing and padding by default."""
    layout = QVBoxLayout()
    layout.setContentsMargins(margin, margin, margin, margin)
    layout.setSpacing(spacing)
    layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    return layout


class SpinBox(QSpinBox):
    """Integer input with default limits for int32."""

    def __init__(self, value: int = 0, bits: int = 32) -> None:
        super(SpinBox, self).__init__()
        self.setMinimum(-2 ** (bits - 1))
        self.setMaximum(2 ** (bits - 1) - 1)
        self.setValue(value)

    def setValueSilent(self, value: int) -> None:
        self.blockSignals(True)
        self.setValue(value)
        self.blockSignals(False)


class USpinBox(QSpinBox):
    """Integer input with default limits for uint31,
    which is the limit of QSpinBox."""

    def __init__(self, value: int = 0, bits: int = 31) -> None:
        super(USpinBox, self).__init__()
        self.setMinimum(0)
        self.setMaximum(2 ** (bits - 1) - 1)
        self.setValue(value)

    def setValueSilent(self, value: int) -> None:
        self.blockSignals(True)
        self.setValue(value)
        self.blockSignals(False)


def spinBox8(value: int) -> SpinBox: return SpinBox(value, 8)


def spinBox16(value: int) -> SpinBox: return SpinBox(value, 16)


def uSpinBox8(value: int) -> USpinBox: return USpinBox(value, 8)


def uSpinBox16(value: int) -> USpinBox: return USpinBox(value, 16)


class DoubleSpinBox(QDoubleSpinBox):
    """Float input with full floating point range."""

    def __init__(self, value: float = 0.0) -> None:
        super(DoubleSpinBox, self).__init__()
        self.setMinimum(-float('inf'))
        self.setMaximum(float('inf'))
        self.setValue(value)
        self.setSingleStep(0.01)
        self.setLineEdit(LineEditSelected())
        self.__prevValue = value

    def setValueSilent(self, value: float) -> None:
        self.blockSignals(True)
        self.setValue(value)
        self.blockSignals(False)

    def focusInEvent(self, event: QFocusEvent) -> None:
        self.__prevValue = self.value()
        super().focusInEvent(event)

    def isDirty(self) -> bool:
        return self.value() != self.__prevValue

class CheckBox(QCheckBox):
    valueChanged = Signal(int)

    def __init__(self, *args: Any) -> None:
        super(CheckBox, self).__init__(*args)
        self.stateChanged.connect(self.valueChanged.emit)

    def value(self) -> bool:
        return self.checkState() == Qt.CheckState.Checked

    def setValue(self, state: bool) -> None:
        self.setCheckState(Qt.CheckState.Checked if state else Qt.CheckState.Unchecked)


class LineEdit(QLineEdit):
    valueChanged = Signal(str)

    def __init__(self, *args: Any) -> None:
        super(LineEdit, self).__init__(*args)
        self.textChanged.connect(self.valueChanged.emit)

    def value(self) -> str:
        return self.text()

    def setValue(self, text: str) -> None:
        self.setText(text)


class LineEditSelected(LineEdit):
    def __init__(self) -> None:
        super(LineEditSelected, self).__init__()
        self.__state = False

    def focusInEvent(self, event: QFocusEvent) -> None:
        super(LineEditSelected, self).focusInEvent(event)
        self.selectAll()
        self.__state = True

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super(LineEditSelected, self).mousePressEvent(event)
        if self.__state:
            self.selectAll()
            self.__state = False


def clearLayout(layout: QLayout) -> None:
    """
    Utility to remove and take ownership of all items in a QLayout,
    xto then have the python GC collector delete it all.
    """
    item = layout.takeAt(0)
    while item:
        if item.layout():
            clearLayout(item.layout())
            item.layout().deleteLater()
        if item.widget():
            item.widget().deleteLater()
        item = layout.takeAt(0)


class EnumBox(QComboBox):
    """
    QComboBox consistent with other editors for interface consistency.
    Not editable so returned integers are directly corresponding to the list of options given to the constructor.
    valueChanged, value and setValue implementations redirected to currentIndexChanged, currentIndex and setCurrentIndex.
    """
    valueChanged = Signal(int)

    def __init__(self, optionList: list[str]) -> None:
        super(EnumBox, self).__init__()
        self.addItems(optionList)
        self.currentIndexChanged.connect(self.valueChanged.emit)
        self.setEditable(False)

    def value(self) -> int:
        return self.currentIndex()

    def setValue(self, index: int) -> None:
        self.setCurrentIndex(index)


class ColorBox(QWidget):
    """
    Default Qt color picker input wrapped in a nice clickable box that previews the color.
    """
    valueChanged = Signal(QColor)

    def __init__(self, color: QColor = QColor()) -> None:
        super(ColorBox, self).__init__()
        self.setMinimumSize(QSize(32, 20))
        self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred))
        self.__color = color
        self.focus = False

    def paintEvent(self, _: Any) -> None:
        painter = QPainter(self)
        painter.setBrush(self.__color)
        painter.drawRect(0, 0, self.width(), self.height())

    def value(self) -> QColor:
        return self.__color

    def setValue(self, color: QColor) -> None:
        self.setValue(color)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.focus = True

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self.focus:
            color = QColorDialog.getColor(self.__color)
            if color.isValid():
                self.__color = color
                self.valueChanged.emit(self.__color)
        self.focus = False
