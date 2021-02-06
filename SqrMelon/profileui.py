import functools

from qtutil import *
from util import randomColor, gSettings


class _ProfileRenderer(QWidget):
    def __init__(self):
        super(_ProfileRenderer, self).__init__()
        self.scene = None
        self.tooltipinfo = {}
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        for label, rect in self.tooltipinfo.items():
            if rect.contains(event.pos()):
                QToolTip.showText(QCursor.pos(), label)

    def paintEvent(self, event):
        if self.scene is None:
            return
        painter = QPainter(self)

        # let's assume we're drawing a timeline for 100ms
        scale = float(self.width()) * 10.0

        cursor = 0.0
        self.tooltipinfo.clear()
        for i, entry in enumerate(self.scene.profileLog):
            label, seconds = entry
            text = '%s %ims' % (label, round(seconds * 1000.0))
            rect = QRectF(cursor * scale, 0, seconds * scale, self.height())
            self.tooltipinfo[text] = rect
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor.fromRgb(*randomColor(i * 0.1357111317)))
            painter.drawRect(rect)
            painter.setPen(Qt.black)
            painter.setBrush(Qt.NoBrush)
            painter.drawText(rect, 0, text)
            cursor += seconds


class Profiler(QWidget):
    """
    Simple utility to draw profile results
    """
    instance = None

    def __init__(self):
        super(Profiler, self).__init__()
        Profiler.instance = self
        self._renderer = _ProfileRenderer()
        self.frameTimes = []
        self.setLayout(vlayout())
        h = QHBoxLayout()
        self._passes = QComboBox()
        h.addWidget(self._passes)
        h.addWidget(QLabel('Color buffer:'))
        self._sub = SpinBox()
        h.addWidget(self._sub)
        self._enabled = CheckBox('Enabled')
        h.addStretch()
        self._enabled.setChecked(gSettings.value('ProfilerEnabled', 'false') == 'true')
        self._enabled.toggled.connect(functools.partial(gSettings.setValue, 'ProfilerEnabled'))
        h.addWidget(self._enabled)
        self.layout().addLayout(h)
        self.layout().addWidget(self._renderer)
        self.layout().setStretch(1, 1)
        self._sub.valueChanged.connect(self._setDebugPass)
        self._passes.currentIndexChanged.connect(self._setDebugPass)

    def isProfiling(self):
        return self._enabled.isChecked()

    def _setDebugPass(self, *args):
        if self._renderer.scene is not None:
            # TODO: should trigger a redraw
            self._renderer.scene.setDebugPass(self._passes.currentIndex() - 1, self._sub.value())

    def setScene(self, scene):
        if scene == self._renderer.scene:
            return

        # clear pass debug info
        self._passes.setCurrentIndex(0)
        self._passes.model().clear()
        self._passes.addItems(['<Not debugging render passes>'])
        self._sub.setValueSilent(0)

        # remove callback
        if self._renderer.scene is not None:
            self._setDebugPass(-1, 0)
            self._renderer.scene.profileInfoChanged.disconnect(self._update)

        self._renderer.scene = scene
        if self._renderer.scene is not None:
            # enforce no debug state
            self._setDebugPass(-1, 0)
            self._renderer.scene.profileInfoChanged.connect(self._update)

            # set up new pass debug info
            for i, passData in enumerate(scene.passes):
                self._passes.addItem(passData.name or ('(nameless pass %s)' % i))

    def _update(self, lastFrameDuration):
        self.frameTimes.append(lastFrameDuration)
        if len(self.frameTimes) > 10:
            self.frameTimes.pop(0)
        averageSecondsPerFrame = float(sum(self.frameTimes) / len(self.frameTimes))
        self.parent().setWindowTitle('Profiler: %i FPS / %i ms' % (round(1.0 / averageSecondsPerFrame), round(averageSecondsPerFrame * 1000.0)))

        if not self.isProfiling():
            return

        self._renderer.repaint()
