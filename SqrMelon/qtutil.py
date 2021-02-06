"""
Imports QT with the right version settings
Exposes a bunch of useful subclasses and utility functions.
"""
from pycompat import *

qt_wrapper = None
try:
    from PySide.QtCore import *
    from PySide.QtGui import *
    from PySide.QtOpenGL import *  # exposed to other code from here

    qt_wrapper = 'PySide'
except ImportError:
    pass
try:
    import sip

    sip.setapi('QString', 2)
    sip.setapi('QVariant', 2)
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
    from PyQt4.QtOpenGL import *  # exposed to other code from here

    qt_wrapper = 'PyQt4'
except ImportError:
    pass
try:
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
    from PyQt5.QtOpenGL import *  # exposed to other code from here
    import html

    pyqtSignal = Signal
    Qt.escape = html.escape
    qt_wrapper = 'PyQt5'
except ImportError:
    pass
try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
    from PySide2.QtOpenGL import *  # exposed to other code from here
    import html

    Qt.escape = html.escape
    pyqtSignal = Signal
    QFileDialog._getSaveFileName = QFileDialog.getSaveFileName
    QFileDialog._getOpenFileName = QFileDialog.getOpenFileName
    QFileDialog._getOpenFileNames = QFileDialog.getOpenFileNames
    QFileDialog._getExistingDirectory = QFileDialog.getExistingDirectory


    def _getSaveFileName(*args):
        return QFileDialog._getSaveFileName(*args)[0]


    def _getOpenFileName(*args):
        return QFileDialog._getOpenFileName(*args)[0]


    def _getOpenFileNames(*args):
        return QFileDialog._getOpenFileNames(*args)[0]


    def _getExistingDirectory(*args):
        return QFileDialog._getExistingDirectory(*args)[0]


    QFileDialog.getSaveFileName = _getSaveFileName
    QFileDialog.getOpenFileName = _getOpenFileName
    QFileDialog.getOpenFileNames = _getOpenFileNames
    QFileDialog.getExistingDirectory = _getExistingDirectory

    qt_wrapper = 'PySide2'
except ImportError:
    pass
assert qt_wrapper, 'No Qt wrapper installed, pip install PySide for python 2 or PySide2 for python 3'


# TODO: floating dockwidget splitter state does not seem to be saved correctly

class QMainWindowState(QMainWindow):
    """
    A MainWindow that remembers its position and dock widget states.
    """

    def __init__(self, settings):
        super(QMainWindowState, self).__init__()
        self.settings = settings
        self.setObjectName(self.__class__.__name__)

    def _store(self):
        self.settings.setValue('%s/geometry' % self.__class__.__name__, self.saveGeometry())
        self.settings.setValue('%s/state' % self.__class__.__name__, self.saveState())

    def _restore(self):
        r = self.settings.value('%s/geometry' % self.__class__.__name__, None)
        if r is not None:
            self.restoreGeometry(r)
        s = self.settings.value('%s/state' % self.__class__.__name__, None)
        if s is not None:
            self.restoreState(s)

    def showEvent(self, event):
        self._restore()

    def hideEvent(self, event):
        self._store()

    def _addDockWidget(self, widget, name=None, where=Qt.RightDockWidgetArea, direction=Qt.Horizontal):
        if name is None:
            name = widget.__class__.__name__
        d = QDockWidget(self)
        d.setWidget(widget)
        d.setObjectName(name)
        d.setWindowTitle(name)
        self.addDockWidget(where, d, direction)
        return d


class QSplitterState(QSplitter):
    """
    A draggable layout that remembers its state.
    """

    def __init__(self, splitterName, orientation):
        super(QSplitterState, self).__init__(orientation)
        self.setObjectName(splitterName)

    def _store(self):
        window = self.window()
        while window.parent():
            window = window.parent().window()
        if hasattr(window, 'settings'):
            window.settings.setValue('%s/state' % self.objectName(), self.saveState())

    def _restore(self):
        window = self.window()
        while window.parent():
            window = window.parent().window()
        if hasattr(window, 'settings'):
            state = window.settings.value('%s/state' % self.objectName())
            if state:
                self.restoreState(state)

    def showEvent(self, event):
        self._restore()

    def hideEvent(self, event):
        self._store()


class Signal(object):
    """
    Signal that's not constrained to qt objects only
    It is not thread safe however.
    """

    def __init__(self):
        self.__connections = []
        self.__active = True

    def connect(self, callback):
        self.__connections.append(callback)

    def disconnect(self, callback):
        self.__connections.remove(callback)

    def emit(self, *args, **kwargs):
        if not self.__active:
            return
        for i in range(len(self.__connections) - 1, -1, -1):
            try:
                self.__connections[i](*args, **kwargs)
            except RuntimeError:
                # wrapped C/C++ object has been deleted, so let's disconnect it too!
                self.__connections.pop(i)
                pass

    def suspend(self):
        self.__active = False

    def resume(self):
        self.__active = True


def hlayout(spacing=0, margin=0):
    """
    Qt layout constructor wrapped to have no spacing and padding by default.
    """
    l = QHBoxLayout()
    l.setMargin(margin)
    l.setSpacing(spacing)
    l.setAlignment(Qt.AlignLeft | Qt.AlignTop)
    return l


def vlayout(spacing=0, margin=0):
    """
    Qt layout constructor wrapped to have no spacing and padding by default.
    """
    l = QVBoxLayout()
    l.setMargin(margin)
    l.setSpacing(spacing)
    l.setAlignment(Qt.AlignLeft | Qt.AlignTop)
    return l


class SpinBox(QSpinBox):
    """
    Integer input with default limits for int32
    """

    def __init__(self, value=0, bits=32):
        super(SpinBox, self).__init__()
        self.setMinimum(-2 ** (bits - 1))
        self.setMaximum(2 ** (bits - 1) - 1)
        self.setValue(value)

    def setValueSilent(self, value):
        self.blockSignals(True)
        self.setValue(value)
        self.blockSignals(False)


class USpinBox(QSpinBox):
    """
    Integer input with default limits for uint32
    """

    def __init__(self, value=0, bits=32):
        super(USpinBox, self).__init__()
        self.setMinimum(0)
        self.setMaximum(2 ** (bits - 1) - 1)
        self.setValue(value)

    def setValueSilent(self, value):
        self.blockSignals(True)
        self.setValue(value)
        self.blockSignals(False)


def spinBox8(value): return SpinBox(value, 8)


def spinBox16(value): return SpinBox(value, 16)


def uSpinBox8(value): return USpinBox(value, 8)


def uSpinBox16(value): return USpinBox(value, 16)


class DoubleSpinBox(QDoubleSpinBox):
    """
    Float input with full floating point range.
    """

    def __init__(self, value=0.0):
        super(DoubleSpinBox, self).__init__()
        self.setMinimum(-float('inf'))
        self.setMaximum(float('inf'))
        self.setValue(value)
        self.setSingleStep(0.01)
        self.setLineEdit(LineEditSelected())

    def setValueSilent(self, value):
        self.blockSignals(True)
        self.setValue(value)
        self.blockSignals(False)


class CheckBox(QCheckBox):
    valueChanged = pyqtSignal(int)

    def __init__(self, *args):
        super(CheckBox, self).__init__(*args)
        self.stateChanged.connect(self.valueChanged.emit)

    def value(self):
        return self.checkState()

    def setValue(self, state):
        self.setCheckState(state)


class LineEdit(QLineEdit):
    valueChanged = pyqtSignal(str)

    def __init__(self, *args):
        super(LineEdit, self).__init__(*args)
        self.textChanged.connect(self.valueChanged.emit)

    def value(self):
        return self.text()

    def setValue(self, text):
        self.setText(text)


class LineEditSelected(LineEdit):
    def __init__(self):
        super(LineEditSelected, self).__init__()
        self.__state = False

    def focusInEvent(self, event):
        super(LineEditSelected, self).focusInEvent(event)
        self.selectAll()
        self.__state = True

    def mousePressEvent(self, event):
        super(LineEditSelected, self).mousePressEvent(event)
        if self.__state:
            self.selectAll()
            self.__state = False


def clearLayout(layout):
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
    valueChanged = pyqtSignal(int)

    def __init__(self, optionList):
        """
        :type optionList: list[str]
        """
        super(EnumBox, self).__init__()
        self.addItems(optionList)
        self.currentIndexChanged.connect(self.valueChanged.emit)
        self.setEditable(False)

    def value(self):
        """
        :rtype: int
        """
        return self.currentIndex()

    def setValue(self, index):
        """
        :type index: int
        """
        self.setCurrentIndex(index)


class ColorBox(QWidget):
    """
    Default Qt color picker input wrapped in a nice clickable box that previews the color.
    """
    valueChanged = pyqtSignal(QColor)

    def __init__(self, color=QColor()):
        """
        :type color: QColor
        """
        super(ColorBox, self).__init__()
        self.setMinimumSize(QSize(32, 20))
        self.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred))
        self.__color = color

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setBrush(self.__color)
        painter.drawRect(0, 0, self.width(), self.height())

    def value(self):
        """
        :rtype: QColor
        """
        return self.__color

    def setValue(self, color):
        """
        :type color: QColor
        """
        self.setValue(color)

    def mousePressEvent(self, event):
        self.focus = True

    def mouseReleaseEvent(self, event):
        if self.focus:
            color = QColorDialog.getColor(self.__color)
            if color.isValid():
                self.__color = color
                self.valueChanged.emit(self.__color)
        self.focus = False
