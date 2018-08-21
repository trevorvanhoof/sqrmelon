from qtutil import *
from experiment.enum import Enum
from utils import lerp
from experiment.serializable import Serializable, AtomSerializable


class EStitchScope(Enum):
    Scene = None  # type: EStitchScope
    Public = None  # type: EStitchScope
    Private = None  # type: EStitchScope

    @staticmethod
    def options():
        return 'Scene', 'Public', 'Private'


EStitchScope.Scene = EStitchScope('Scene')
EStitchScope.Public = EStitchScope('Public')
EStitchScope.Private = EStitchScope('Private')


class Stitch(Serializable):
    def initialize(self, name, scope=EStitchScope.Public):
        self.name = name
        self.scope = scope

    @classmethod
    def serializableProperties(cls):
        yield 'name'
        yield 'scope', EStitchScope


class Plug(Serializable):
    def initialize(self, name, node):
        self.name = name
        self.node = node
        self.connections = []
        self._portRect = None
        self._textRect = None

    @classmethod
    def serializableProperties(cls):
        yield 'name'
        yield 'connections'

    @property
    def portRect(self):
        return self._portRect

    @property
    def textRect(self):
        return self._textRect

    def paint(self, painter):
        painter.drawEllipse(self._portRect)
        painter.drawText(self._textRect, Qt.AlignRight | Qt.AlignTop, self.name)


class OutputPlug(Plug):
    def initialize(self, name, node, size=-1):
        super(OutputPlug, self).initialize(name, node)
        # if size is negative it is a factor of the screen resolution
        self.size = size

    @classmethod
    def serializableProperties(cls):
        yield 'name'
        yield 'size'
        yield 'connections'


class Node(Serializable):
    def initialize(self, name, x=0, y=0):
        self.name = name
        self.x = x
        self.y = y
        self._rect = None
        self._contentRect = None
        self.inputs = []
        self.outputs = []
        self.stitches = []

    def postInitialize(self):
        self.layout()

    @classmethod
    def serializableProperties(cls):
        yield 'name'
        yield 'x'
        yield 'y'
        yield 'inputs'
        yield 'outputs'
        yield 'stitches'

    def setName(self, name):
        self.name = name

    def setPosition(self, x, y):
        self.x = x
        self.y = y
        dx = (x - self._rect.x())
        dy = (y - self._rect.y())
        self._rect.moveTo(x, y)
        self._contentRect.moveTo(x + Node.PADDING, y + Node.PADDING)
        for plug in self.inputs + self.outputs:
            x, y = plug._portRect.x() + dx, plug._portRect.y() + dy
            plug._portRect.moveTo(x, y)
            x, y = plug._textRect.x() + dx, plug._textRect.y() + dy
            plug._textRect.moveTo(x, y)

    @property
    def rect(self):
        if self._rect is None:
            self.layout()
        return self._rect

    PADDING = 4

    def layout(self):
        PLUGSIZE = 7

        metrics = QApplication.fontMetrics()
        padding = Node.PADDING
        em = max(PLUGSIZE, metrics.height()) + padding

        lhs = 0.0
        if self.inputs:
            lhs = max(PLUGSIZE + padding + metrics.width(input.name) + padding for input in self.inputs)
        rhs = 0.0
        if self.outputs:
            rhs = max(PLUGSIZE + padding + metrics.width(output.name) + padding for output in self.outputs)
        contentWidth = max(lhs + rhs, metrics.width(self.name))
        self._contentRect = QRect(self.x + padding, self.y + padding, contentWidth, em * (1 + max(len(self.inputs), len(self.outputs))))
        self._rect = QRect(self.x, self.y, contentWidth + 2 * padding, em * (1 + max(len(self.inputs), len(self.outputs))) + 2 * padding)

        contentRect = self._contentRect.adjusted(0, em, 0, 0)
        for i in xrange(max(len(self.inputs), len(self.outputs))):
            o = ((em - padding) - PLUGSIZE) / 2
            if i < len(self.inputs):
                self.inputs[i]._portRect = QRect(contentRect.x(), contentRect.y() + o, PLUGSIZE, PLUGSIZE)
                self.inputs[i]._textRect = QRect(contentRect.x() + PLUGSIZE + padding, contentRect.y(), lhs - (PLUGSIZE + padding), metrics.height())
            if i < len(self.outputs):
                self.outputs[i]._portRect = QRect(contentRect.right() - PLUGSIZE, contentRect.y() + o, PLUGSIZE, PLUGSIZE)
                self.outputs[i]._textRect = QRect(contentRect.right() - rhs, contentRect.y(), rhs - (PLUGSIZE + padding), contentRect.height())
            contentRect.adjust(0, em, 0, 0)

    def paint(self, painter):
        path = QPainterPath()
        path.addRoundedRect(QRectF(self._rect), Node.PADDING, Node.PADDING)
        painter.fillPath(path, QColor(220, 220, 220))
        painter.drawText(self._contentRect, Qt.AlignHCenter | Qt.AlignTop, self.name)
        for input in self.inputs:
            input.paint(painter)
            # connections are bidirectional, so by only painting connections for inputs we cover all of them
            for other in input.connections:
                start = input._portRect.center()
                end = other._portRect.center()
                path = QPainterPath()
                path.moveTo(start)
                path.cubicTo(QPoint(lerp(start.x(), end.x(), 0.5), start.y()), QPoint(lerp(end.x(), start.x(), 0.5), end.y()), end)
                painter.drawPath(path)
        for output in self.outputs:
            output.paint(painter)
