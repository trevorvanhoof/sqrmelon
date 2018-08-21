from qtutil import *
from experiment.curvemodel import HermiteCurve, HermiteKey, ELoopMode
from experiment.model import Clip, Shot, Event
from experiment.timelineview import TimelineView
from experiment.timer import Time
from experiment.widgets import ClipManager, CurveUI, EventModel, ShotModel, FilteredView

if __name__ == '__main__':
    app = QApplication([])
    settings = QSettings('PB', 'experimental')

    undoStack = QUndoStack()
    undoView = QUndoView(undoStack)

    clip0 = Clip('Clip 0')
    clip0.curves.appendRow(HermiteCurve('uOrigin.x', ELoopMode.Clamp, [HermiteKey(0.0, 0.0, 0.0, 0.0), HermiteKey(4.0, 1.0, 1.0, 1.0)]).items)
    clip0.curves.appendRow(HermiteCurve('uFlash', ELoopMode.Clamp, [HermiteKey(0.0, 1.0, 1.0, 1.0), HermiteKey(1.0, 0.0, 0.0, 0.0)]).items)

    clip1 = Clip('Clip 1')
    clip1.curves.appendRow(HermiteCurve('uOrigin.x', ELoopMode.Clamp, [HermiteKey(2.0, 0.0, 0.0, 0.0), HermiteKey(3.0, 1.0, 0.0, 0.0)]).items)
    clip1.curves.appendRow(HermiteCurve('uOrigin.y', ELoopMode.Clamp, [HermiteKey(0.0, 0.0, 1.0, 1.0), HermiteKey(1.0, 1.0, 1.0, 1.0)]).items)

    model = QStandardItemModel()
    selectionModel = QItemSelectionModel(model)

    # TODO: Edits in these views are not undoable, but I would like to mass-edit in the future
    shotManager = FilteredView(undoStack, ShotModel(model))
    shotManager.model().appendRow(Shot('New Shot', 'Scene 1', 0.0, 4.0, 0).items)

    eventManager = FilteredView(undoStack, EventModel(model))
    eventManager.model().appendRow(Event('New event', clip0, 0.0, 4.0, 1.0, 0.0, 2).items)
    eventManager.model().appendRow(Event('New event', clip0, 0.0, 1.0, 1.0, 0.0, 1).items)
    eventManager.model().appendRow(Event('New event', clip1, 1.0, 2.0, 0.5, 0.0, 1).items)

    # changing the model contents seems to mess with the column layout stretch
    model.rowsInserted.connect(shotManager.updateSections)
    model.rowsInserted.connect(eventManager.updateSections)
    model.rowsRemoved.connect(shotManager.updateSections)
    model.rowsRemoved.connect(eventManager.updateSections)

    eventManager.model().appendRow(Event('New event', clip0, 2.0, 4.0, 0.25, 0.0, 1).items)

    clipManager = ClipManager(eventManager, undoStack)
    clipManager.model().appendRow(clip0.items)
    clipManager.model().appendRow(clip1.items)

    timer = Time()
    # TODO: Curve renames and loop mode changes are not undoable
    curveUI = CurveUI(timer, eventManager, clipManager, undoStack)


    def eventChanged():
        for event in eventManager.selectionModel().selectedRows():
            curveUI.setEvent(event.data(Qt.UserRole + 1))
            return
        curveUI.setEvent(None)


    eventManager.selectionChange.connect(eventChanged)

    eventTimeline = TimelineView(timer, undoStack, model, selectionModel)

    mainWindow = QMainWindowState(settings)
    mainWindow.setDockNestingEnabled(True)
    mainWindow.createDockWidget(undoView)
    mainWindow.createDockWidget(clipManager)
    mainWindow.createDockWidget(curveUI)
    mainWindow.createDockWidget(shotManager, name='Shots')
    mainWindow.createDockWidget(eventManager, name='Events')
    mainWindow.createDockWidget(eventTimeline)

    mainWindow.show()
    # makes sure qt cleans up & python stops after closing the main window; https://stackoverflow.com/questions/39304366/qobjectstarttimer-qtimer-can-only-be-used-with-threads-started-with-qthread
    mainWindow.setAttribute(Qt.WA_DeleteOnClose)

    app.exec_()
