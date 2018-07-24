from experiment.widgets import ClipManager, EventTimeline, ShotManager
from experiment.curvemodel import HermiteCurve, HermiteKey
from experiment.modelbase import Shot, Event, Clip
from experiment.curveview import CurveWidget
from experiment.enums import ELoopMode
from qtutil import *


def testCurves():
    testCurve = HermiteCurve()
    testCurve.keys.append(HermiteKey(0.0, 0.0, 0.0, 0.0))
    k1 = HermiteKey(1.0, 1.0, 0.0, 0.0)
    testCurve.keys.append(k1)
    k2 = HermiteKey(2.0, 0.0, 0.0, 0.0)
    testCurve.keys.append(k2)
    k3 = HermiteKey(4.0, 1.0, 0.0, 0.0)
    testCurve.keys.append(k3)
    k4 = HermiteKey(6.0, 0.0, 0.0, 1.0)
    testCurve.keys.append(k4)
    k5 = HermiteKey(7.0, 1.0, 1.0, -1.0)
    testCurve.keys.append(k5)
    testCurve.keys.append(HermiteKey(8.0, 0.0, -1.0, 1.0))
    testCurve.keys.append(HermiteKey(12.0, 1.0, 1.0, 0.0))
    from collections import OrderedDict
    d = OrderedDict()
    d['uOrigin.x'] = testCurve
    return d


def run():
    a = QApplication([])

    w = QMainWindow()
    w.setAttribute(Qt.WA_DeleteOnClose)  # makes sure qt cleans up & python stops after closing the main window; https://stackoverflow.com/questions/39304366/qobjectstarttimer-qtimer-can-only-be-used-with-threads-started-with-qthread

    m = QMenuBar()
    w.setMenuBar(m)
    editMenu = m.addMenu('&Edit')

    s = QSplitter(Qt.Vertical)
    w.setCentralWidget(s)

    undoStack = QUndoStack()
    undoView = QUndoView(undoStack)
    s.addWidget(undoView)

    clipManager = ClipManager(undoStack)
    clip0 = Clip('New Clip', ELoopMode('Clamp'))
    clip0.curves.update(testCurves())
    clipManager.model().appendRow(clip0.items)
    s.addWidget(clipManager)

    shotManager = ShotManager()
    shotManager.model().appendRow(Shot('New Shot', 'Scene 1', clip0, 0.0, 4.0, 1.0, 0.0).items)
    shotManager.model().appendRow(Event('New event', clip0, 0.0, 1.0, 1.0, 0.0).items)
    shotManager.model().appendRow(Event('New event', clip0, 1.0, 2.0, 0.5, 0.0).items)
    shotManager.model().appendRow(Event('New event', clip0, 2.0, 4.0, 0.25, 0.0).items)
    s.addWidget(shotManager)

    eventTimeline = EventTimeline(shotManager.model())
    s.addWidget(eventTimeline)

    ac = undoStack.createUndoAction(w)
    ac.setShortcut(QKeySequence('Ctrl+Z'))
    editMenu.addAction(ac)

    curveView = CurveWidget(undoStack)
    s.addWidget(curveView)
    clipManager.focusCurves.connect(curveView.focusCurves)

    w.show()
    a.exec_()


if __name__ == '__main__':
    run()
