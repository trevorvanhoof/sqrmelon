from qtutil import *
from experiment.curvemodel import HermiteCurve, HermiteKey
from experiment.enums import ELoopMode
from experiment.model import Clip, Shot, Event
from experiment.timelineview import TimelineView
from experiment.widgets import CurveList, ShotManager, CurveView, ClipManager, EventManager

if __name__ == '__main__':
    app = QApplication([])
    settings = QSettings('PB', 'experimental')

    undoStack = QUndoStack()
    undoView = QUndoView(undoStack)

    clip0 = Clip('Clip 0', ELoopMode('Clamp'))
    clip0.curves.appendRow(HermiteCurve('uOrigin.x', ELoopMode('Clamp'), [HermiteKey(0.0, 0.0, 0.0, 0.0), HermiteKey(1.0, 1.0, 1.0, 1.0)]).items)
    clip0.curves.appendRow(HermiteCurve('uFlash', ELoopMode('Clamp'), [HermiteKey(0.0, 1.0, 1.0, 1.0), HermiteKey(1.0, 0.0, 0.0, 0.0)]).items)

    clip1 = Clip('Clip 1', ELoopMode('Loop'))
    clip1.curves.appendRow(HermiteCurve('uOrigin.x', ELoopMode('Clamp'), [HermiteKey(2.0, 0.0, 0.0, 0.0), HermiteKey(3.0, 1.0, 0.0, 0.0)]).items)
    clip1.curves.appendRow(HermiteCurve('uOrigin.y', ELoopMode('Clamp'), [HermiteKey(0.0, 0.0, 1.0, 1.0), HermiteKey(1.0, 1.0, 1.0, 1.0)]).items)

    shotManager = ShotManager(undoStack)
    shotManager.model().appendRow(Shot('New Shot', 'Scene 1', 0.0, 4.0, 0).items)

    eventManager = EventManager(undoStack)
    eventManager.model().appendRow(Event('New event', clip0, 0.0, 4.0, 1.0, 0.0, 2).items)
    eventManager.model().appendRow(Event('New event', clip0, 0.0, 1.0, 1.0, 0.0, 1).items)
    eventManager.model().appendRow(Event('New event', clip1, 1.0, 2.0, 0.5, 0.0, 1).items)
    eventManager.model().appendRow(Event('New event', clip0, 2.0, 4.0, 0.25, 0.0, 1).items)

    clipManager = ClipManager(eventManager, undoStack)
    clipManager.model().appendRow(clip0.items)
    clipManager.model().appendRow(clip1.items)

    curveList = CurveList(clipManager, undoStack)

    curveView = CurveView(curveList, undoStack)

    eventTimeline = TimelineView(shotManager.model(), eventManager.model())

    mainWindow = QMainWindowState(settings)
    mainWindow.setDockNestingEnabled(True)
    mainWindow.createDockWidget(undoView)
    mainWindow.createDockWidget(clipManager)
    mainWindow.createDockWidget(curveList)
    mainWindow.createDockWidget(curveView)
    mainWindow.createDockWidget(shotManager)
    mainWindow.createDockWidget(eventManager)
    mainWindow.createDockWidget(eventTimeline)

    mainWindow.show()
    # makes sure qt cleans up & python stops after closing the main window; https://stackoverflow.com/questions/39304366/qobjectstarttimer-qtimer-can-only-be-used-with-threads-started-with-qthread
    mainWindow.setAttribute(Qt.WA_DeleteOnClose)

    app.exec_()
