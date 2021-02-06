try:
    # Python 2 support
    import OSC
    from OSC import OSCClientError
except ImportError:
    # Python 3 support
    import pyOSC3 as OSC
    from pyOSC3 import OSCClientError

from audioLibs import createSong
from qtutil import *
import time
from math import floor
from xml.etree import cElementTree

import icons
from util import gSettings, toPrettyXml, currentProjectFilePath, currentProjectDirectory


class OSCClient(object):
    def __init__(self):
        self.__client = OSC.OSCClient()
        self.__client.connect(('127.0.0.1', 2223))
        self.__isPlaying = False

    def __del__(self):
        self.__client.close()

    def __sendSilent(self, msg):
        # silently ignore any failure while sending
        try:
            self.__client.send(msg)
        except OSCClientError:
            return

    def setPosition(self, time):
        if self.__isPlaying:
            return
        msg = OSC.OSCMessage()
        msg.setAddress('/position')
        msg.append(time)
        self.__sendSilent(msg)

    def setBpm(self, bpm):
        msg = OSC.OSCMessage()
        msg.setAddress('/bpm')
        msg.append(bpm)
        self.__sendSilent(msg)

    def play(self):
        msg = OSC.OSCMessage()
        msg.setAddress('/play')
        msg.append(1)
        self.__sendSilent(msg)
        self.__isPlaying = True

    def pause(self):
        msg = OSC.OSCMessage()
        msg.setAddress('/play')
        msg.append(0)
        self.__sendSilent(msg)
        self.__isPlaying = False

    def scrub(self, state):
        msg = OSC.OSCMessage()
        msg.setAddress('/scrub')
        msg.append(state)
        self.__sendSilent(msg)

    def loop(self, start, end):
        msg = OSC.OSCMessage()
        msg.setAddress('/loopstart')
        msg.append(start)
        self.__sendSilent(msg)
        msg = OSC.OSCMessage()
        msg.setAddress('/looplength')
        msg.append(end - start)
        self.__sendSilent(msg)


class Timer(object):
    minTimeChanged = Signal()
    startChanged = Signal()
    endChanged = Signal()
    maxTimeChanged = Signal()
    timeChanged = Signal()
    timeLooped = Signal()
    bpmChanged = Signal()

    def __init__(self):
        self.__osc = OSCClient()

        self.__start = 0.0
        self.__end = 10.0
        self.__minTime = 0.0
        self.__maxTime = 100.0
        self.__BPS = 60.0
        self.__time = 0.0

        self.timeChanged.connect(self.__osc.setPosition)
        self.startChanged.connect(self.__oscSetLoopRange)
        self.endChanged.connect(self.__oscSetLoopRange)

        self.projectOpened()

        if self.__maxTime == self.__minTime:
            self.__maxTime += 1.0
        self.__timer = QTimer()
        self.__timer.timeout.connect(self.__tick)
        self.__prevTime = None

    def __oscSetLoopRange(self, *args):
        self.__osc.loop(self.__start, self.__end)

    def oscScrub(self, state):
        self.__osc.scrub(state)

    @property
    def bpm(self):
        return self.__BPS * 60.0

    @bpm.setter
    def bpm(self, bpm):
        self.__BPS = bpm / 60.0
        self.bpmChanged.emit(bpm)

    def setBpm(self, bpm):
        self.__BPS = bpm / 60.0
        self.__osc.setBpm(int(bpm))
        self.bpmChanged.emit(bpm)

    def secondsToBeats(self, seconds):
        return seconds * self.__BPS

    def beatsToSeconds(self, beats):
        return beats / self.__BPS

    def kick(self):
        self.timeChanged.emit(self.time)

    def projectOpened(self):
        self.start = float(gSettings.value('TimerStartTime', 0.0))
        endTime = float(gSettings.value('TimerEndTime', 8.0))
        self.time = float(gSettings.value('TimerTime', 0.0))

        project = currentProjectFilePath()
        if project and project.exists():
            text = project.content()

            try:
                root = cElementTree.fromstring(text)
            except:
                root = None

            if root is not None:
                self.minTime = float(root.attrib.get('TimerMinTime', 0.0))
                self.maxTime = float(root.attrib.get('TimerMaxTime', 8.0))
                self.end = min(endTime, self.maxTime)

                self.__BPS = float(root.attrib.get('TimerBPS', 2.0))
                self.__osc.setBpm(int(round(self.__BPS * 60)))
                self.bpmChanged.emit(self.__BPS * 60.0)
                return

        # legacy project / creating new project
        self.minTime = 0.0
        self.maxTime = 4.0
        self.end = min(endTime, self.maxTime)

        self.__BPS = float(gSettings.value('TimerBPS', 2.0))
        self.__osc.setBpm(int(round(self.__BPS * 60)))
        self.bpmChanged.emit(self.__BPS * 60.0)

    def saveState(self):
        gSettings.setValue('TimerStartTime', self.__start)
        gSettings.setValue('TimerEndTime', self.__end)
        gSettings.setValue('TimerTime', self.__time)

        project = currentProjectFilePath()
        if not project or not project.exists():
            # legacy project or no project open
            gSettings.setValue('TimerMinTime', self.__minTime)
            gSettings.setValue('TimerMaxTime', self.__maxTime)
            gSettings.setValue('TimerBPS', self.__BPS)
            return
        root = cElementTree.Element('Project')
        root.attrib['TimerMinTime'] = str(self.__minTime)
        root.attrib['TimerMaxTime'] = str(self.__maxTime)
        root.attrib['TimerBPS'] = str(self.__BPS)
        with project.edit() as fh:
            fh.write(toPrettyXml(root))

    def goToStart(self):
        self.time = self.__start

    def stepBack(self):
        if self.time - 1.0 < self.__start:
            self.time = self.__end
        else:
            self.time -= 1.0

    def __tick(self):
        if self.__prevTime is None:
            self.__prevTime = time.time()
            return
        delta = time.time() - self.__prevTime
        self.__prevTime = time.time()

        delta = self.secondsToBeats(delta)

        t = self.__time + delta - self.__start
        r = self.__end - self.__start
        loop = floor(t / r)
        self.__time = t - loop * r + self.__start
        self.timeChanged.emit(self.time)
        if loop != 0:
            self.timeLooped.emit(self.time)

    def isPlaying(self):
        return self.__timer.isActive()

    def playPause(self):
        if self.__timer.isActive():
            self.__prevTime = None
            self.__timer.stop()
            self.__osc.pause()
        else:
            self.__timer.start(1.0 / 60.0)
            self.__osc.play()

    def stepNext(self):
        if self.time + 1.0 > self.__end:
            self.time = self.__start
        else:
            self.time += 1.0

    def goToEnd(self):
        self.__time = self.__end

    @property
    def minTime(self):
        return self.__minTime

    @property
    def start(self):
        return self.__start

    @property
    def end(self):
        return self.__end

    @property
    def maxTime(self):
        return self.__maxTime

    @property
    def time(self):
        return self.__time

    @minTime.setter
    def minTime(self, value):
        if self.__minTime == value: return
        self.__minTime = value
        self.minTimeChanged.emit(value)

    @start.setter
    def start(self, value):
        if self.__start == value: return
        self.__start = value
        self.startChanged.emit(value)

    @end.setter
    def end(self, value):
        if self.__end == value: return
        self.__end = value
        self.endChanged.emit(value)

    @maxTime.setter
    def maxTime(self, value):
        if self.__maxTime == value: return
        self.__maxTime = value
        self.maxTimeChanged.emit(value)

    @time.setter
    def time(self, value):
        if self.__time == value: return
        self.__time = value
        self.timeChanged.emit(value)

    def setMinTime(self, value):
        self.minTime = value
        clamped = max(self.__start, self.__minTime)
        if clamped != self.__start:
            self.__start = clamped
            self.startChanged.emit(value)

    def setStart(self, value):
        self.start = value
        clamped = min(self.__minTime, self.__start)
        if clamped != self.__minTime:
            self.__minTime = clamped
            self.minTimeChanged.emit(value)

    def setEnd(self, value):
        self.end = value
        clamped = max(self.__maxTime, self.__end)
        if clamped != self.__maxTime:
            self.__maxTime = clamped
            self.maxTimeChanged.emit(value)

    def setMaxTime(self, value):
        self.maxTime = value
        clamped = min(self.__end, self.__maxTime)
        if clamped != self.__end:
            self.__end = clamped
            self.endChanged.emit(value)

    def setTime(self, value):
        self.time = value


class TimeLine(QWidget):
    valueChanged = pyqtSignal(float)

    def __init__(self, timer, shotsManager):
        super(TimeLine, self).__init__()
        self.__shotsManager = shotsManager
        timer.startChanged.connect(self.__onRepaint)
        timer.endChanged.connect(self.__onRepaint)
        timer.timeChanged.connect(self.__onRepaint)
        self.__timer = timer
        self.setMinimumWidth(128)

    def __onRepaint(self, *args):
        self.repaint()

    def _selectTime(self, x):
        x = min(max(x / float(self.width()), 0.0), 1.0)
        self.__timer.time = x * (self.__timer.end - self.__timer.start) + self.__timer.start
        self.valueChanged.emit(self.__timer.time)

    def __shotGeometry(self):
        dt = float(self.__timer.end - self.__timer.start)
        if dt:
            normalizeFactor = 1.0 / dt
        else:
            normalizeFactor = 0.0
        visibleWidth = self.width() - 1
        for i, shot in enumerate(self.__shotsManager.shots()):
            if not shot.enabled:
                continue
            paramStart = (shot.start - self.__timer.start) * normalizeFactor
            paramEnd = (shot.end - self.__timer.start) * normalizeFactor
            if (paramStart < 0.0 and paramEnd < 0.0) or (paramStart > 1.0 and paramEnd > 1.0):
                continue
            r = QRect(QPoint(paramStart * visibleWidth, 4), QPoint(paramEnd * visibleWidth, 17))
            yield i, shot, r

    def mousePressEvent(self, event):
        if event.modifiers() & Qt.ControlModifier == Qt.ControlModifier:
            # not moving time, just trying to select a shot
            for i, shot, r in self.__shotGeometry():
                if r.contains(event.pos()):
                    self.__shotsManager.selectShot(shot)
                    break
            return
        self.__timer.oscScrub(1)
        self._selectTime(event.x())

    def mouseMoveEvent(self, event):
        if event.modifiers() & Qt.ControlModifier == Qt.ControlModifier:
            return
        self._selectTime(event.x())

    def mouseReleaseEvent(self, event):
        if event.modifiers() & Qt.ControlModifier == Qt.ControlModifier:
            return
        self.__timer.oscScrub(0)

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.fillRect(QRect(QPoint(0, 4), self.size() - QSize(1, 10)), QColor.fromRgb(210, 210, 210))

        dt = float(self.__timer.end - self.__timer.start)
        if dt:
            normalizeFactor = 1.0 / dt
        else:
            normalizeFactor = 0.0
        visibleWidth = self.width() - 1
        for i, shot, r in self.__shotGeometry():
            painter.fillRect(r, shot.color)
            if shot.pinned:
                pen = painter.pen()
                painter.setPen(Qt.red)
                painter.drawRect(r)
                painter.setPen(pen)
            r.adjust(5, 0, 0, 0)
            painter.drawText(r, 0, shot.name)

        paramTime = (self.__timer.time - self.__timer.start) * normalizeFactor
        pixelX = int(paramTime * visibleWidth)
        painter.setPen(Qt.red)
        painter.drawLine(pixelX, 0, pixelX, self.height() - 3)

        painter.drawPixmap(pixelX - 4, 0, icons.getImage('TimeMarkerTop-24'))


class RangeSlider(QWidget):
    HANDLE_SIZE = 24

    def __init__(self, timer):
        super(RangeSlider, self).__init__()
        timer.minTimeChanged.connect(self.__onRepaint)
        timer.maxTimeChanged.connect(self.__onRepaint)
        timer.startChanged.connect(self.__onRepaint)
        timer.endChanged.connect(self.__onRepaint)
        self.__timer = timer
        self.__drag = None
        self.setMinimumWidth(RangeSlider.HANDLE_SIZE * 6)

    def __onRepaint(self, *args):
        self.repaint()

    def _handleRects(self):
        w = self.width() - RangeSlider.HANDLE_SIZE * 2 - 1
        sx = (self.__timer.start - self.__timer.minTime) / float(self.__timer.maxTime - self.__timer.minTime)
        ex = (self.__timer.end - self.__timer.minTime) / float(self.__timer.maxTime - self.__timer.minTime)
        sx *= w
        ex *= w

        return (QRect(QPoint(sx, 0), QSize(RangeSlider.HANDLE_SIZE, self.height() - 1)),
                QRect(QPoint(ex + RangeSlider.HANDLE_SIZE, 0), QSize(RangeSlider.HANDLE_SIZE, self.height() - 1)),
                QRect(QPoint(sx + RangeSlider.HANDLE_SIZE, 0), QSize(ex - sx, self.height() - 1)))

    def mousePressEvent(self, event):
        left, right, both = self._handleRects()
        left = left.contains(event.pos())
        right = right.contains(event.pos())
        both = both.contains(event.pos())
        left |= both
        right |= both
        if not left and not right:
            return
        self.__drag = left, right, event.x(), self.__timer.start, self.__timer.end

    def mouseMoveEvent(self, event):
        EPSILON = 0.01  # avoid division by 0
        if self.__drag is None:
            return
        delta = event.x() - self.__drag[2]
        delta = (delta / float(self.width())) * (self.__timer.maxTime - self.__timer.minTime)
        delta = round(delta)
        # make sure ranges are in min/max range
        if self.__drag[0] and self.__drag[1]:
            self.__timer.start = min(max(self.__drag[3] + delta, self.__timer.minTime), self.__timer.maxTime - EPSILON)
            self.__timer.end = min(max(self.__drag[4] + delta, self.__timer.minTime + EPSILON), self.__timer.maxTime)
        elif self.__drag[0]:
            self.__timer.start = min(max(self.__drag[3] + delta, self.__timer.minTime), self.__timer.end - EPSILON)
        elif self.__drag[1]:
            self.__timer.end = min(max(self.__drag[4] + delta, self.__timer.start + EPSILON), self.__timer.maxTime)

    def mouseReleaseEvent(self, event):
        self.__drag = None

    def _drawGrip(self, painter, rect):
        painter.setPen(QColor.fromRgb(148, 148, 148))
        painter.drawLine(rect.center().x() - 2, rect.top() + 4, rect.center().x() - 2, rect.bottom() - 3)
        painter.drawLine(rect.center().x(), rect.top() + 4, rect.center().x(), rect.bottom() - 3)
        painter.drawLine(rect.center().x() + 2, rect.top() + 4, rect.center().x() + 2, rect.bottom() - 3)

    def _drawButton(self, painter, rect, baseColor, alwaysDrawGrip):
        painter.fillRect(rect, baseColor)
        painter.setPen(QColor.fromRgb(255, 255, 255))
        painter.drawLine(rect.left() + 1, rect.top() + 1, rect.right() - 1, rect.top() + 1)
        painter.drawLine(rect.left() + 1, rect.top() + 1, rect.left() + 1, rect.bottom() - 1)

        painter.setPen(QColor.fromRgb(92, 92, 92))
        painter.drawRect(rect)

        if alwaysDrawGrip or rect.width() > 32:
            self._drawGrip(painter, rect)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(QRect(QPoint(0, 4), self.size() - QSize(1, 10)), QColor.fromRgb(210, 210, 210))
        rects = self._handleRects()
        self._drawButton(painter, rects[0], QColor.fromRgb(210, 210, 210), True)
        self._drawButton(painter, rects[1], QColor.fromRgb(210, 210, 210), True)
        self._drawButton(painter, rects[2], QColor.fromRgb(180, 180, 180), False)


def muteState():
    return gSettings.value('mute', 'False') == 'True'


def setMuteState(state):
    gSettings.setValue('mute', str(bool(state)))


class TimestampDisplay(QLabel):
    def __init__(self, timer):
        super(TimestampDisplay, self).__init__()
        self.__timer = timer
        self.update()

    def update(self, *args):
        beat = self.__timer.time
        minute = int(beat / self.__timer.bpm)
        second = int(((beat * 60) / self.__timer.bpm) % 60)
        fraction = int(round(((beat * 60 * 1000) / self.__timer.bpm) % 1000))
        self.setText('%02d:%02d,%04d' % (minute, second, fraction))


class BPMInput(QWidget):
    def __init__(self, bpm):
        super(BPMInput, self).__init__()
        bpm = round(bpm, 2)
        self._spinBox = DoubleSpinBox(bpm)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self._spinBox)
        self._label = QLabel('%s BPM' % bpm)
        self.layout().addWidget(self._label)
        self._spinBox.hide()
        self._spinBox.editingFinished.connect(self.disable)

    def spinBox(self):
        return self._spinBox

    def setValueSilent(self, bpm):
        bpm = round(bpm, 2)
        self._spinBox.setValueSilent(bpm)
        self._label.setText('%s BPM' % bpm)

    def disable(self):
        self._label.show()
        self._label.setText('%s BPM' % self._spinBox.value())
        self._spinBox.hide()

    def mouseDoubleClickEvent(self, *args, **kwargs):
        self._spinBox.show()
        self._spinBox.setFocus(Qt.MouseFocusReason)
        self._spinBox.selectAll()
        self._label.hide()


class TimeSlider(QWidget):
    def __init__(self, timer, shotsManager):
        super(TimeSlider, self).__init__()

        main = vlayout()
        self.setLayout(main)

        self.__soundtrack = None
        self.__soundtrackPath = None

        layout = hlayout()
        main.addLayout(layout)
        timeline = TimeLine(timer, shotsManager)
        layout.addWidget(timeline)
        currentTime = DoubleSpinBox(timer.time)
        currentTime.setToolTip('Current time in beats')
        currentTime.setStatusTip('Current time in beats')
        currentTime.setMinimumWidth(70)
        currentTime.setDecimals(2)
        currentTime.valueChanged.connect(timer.setTime)
        timer.timeChanged.connect(currentTime.setValueSilent)
        layout.addWidget(currentTime)

        currentSeconds = TimestampDisplay(timer)
        currentSeconds.setToolTip('Current time in minutes:seconds,milliseconds')
        currentSeconds.setStatusTip('Current time in minutes:seconds,milliseconds')
        currentSeconds.setMinimumWidth(70)
        layout.addWidget(currentSeconds)
        timer.timeChanged.connect(currentSeconds.update)

        bpm = BPMInput(int(round(timer.bpm)))
        bpm.setToolTip('Beats per minute')
        bpm.setStatusTip('Beats per minute, determines playback speed')
        bpm.spinBox().setMinimum(1)
        bpm.spinBox().valueChanged.connect(timer.setBpm)
        timer.bpmChanged.connect(bpm.setValueSilent)
        layout.addWidget(bpm)

        goToStart = QPushButton(icons.get('Rewind-48'), '')
        goToStart.setToolTip('Go to start')
        goToStart.setStatusTip('Go to start')
        goToStart.clicked.connect(timer.goToStart)
        goToStart.setFixedWidth(24)
        layout.addWidget(goToStart)

        stepBack = QPushButton(icons.get('Skip to Start-48'), '')
        stepBack.setToolTip('Step back')
        stepBack.setStatusTip('Step back')
        stepBack.clicked.connect(timer.stepBack)
        stepBack.setFixedWidth(24)
        layout.addWidget(stepBack)

        self.__playPause = QPushButton(icons.get('Play-48'), '')
        self.__playPause.setToolTip('Play')
        self.__playPause.setStatusTip('Play')
        self.__playPause.setFixedWidth(24)
        layout.addWidget(self.__playPause)
        shortcut0 = QShortcut(self)
        shortcut0.setKey(QKeySequence(Qt.Key_Space))
        shortcut0.setContext(Qt.ApplicationShortcut)
        shortcut1 = QShortcut(self)
        shortcut1.setKey(QKeySequence(Qt.Key_P))
        shortcut1.setContext(Qt.ApplicationShortcut)
        self.__playPause.clicked.connect(self.__togglePlayPause)
        self.__playPause.clicked.connect(timer.playPause)
        shortcut0.activated.connect(self.__togglePlayPause)
        shortcut0.activated.connect(timer.playPause)
        shortcut1.activated.connect(self.__togglePlayPause)
        shortcut1.activated.connect(timer.playPause)

        stepNext = QPushButton(icons.get('End-48'), '')
        stepNext.setToolTip('Step forwards')
        stepNext.setStatusTip('Step forwards')
        stepNext.clicked.connect(timer.stepNext)
        stepNext.setFixedWidth(24)
        layout.addWidget(stepNext)

        goToEnd = QPushButton(icons.get('Fast Forward-48'), '')
        goToEnd.setToolTip('Go to end')
        goToEnd.setStatusTip('Go to end')
        goToEnd.clicked.connect(timer.goToEnd)
        goToEnd.setFixedWidth(24)
        layout.addWidget(goToEnd)
        layout.setStretch(0, 1)

        layout = hlayout()
        main.addLayout(layout)

        minTime = DoubleSpinBox(timer.minTime)
        startTime = DoubleSpinBox(timer.start)
        endTime = DoubleSpinBox(timer.end)
        maxTime = DoubleSpinBox(timer.maxTime)

        endTime.setMinimum(startTime.value() + 0.01)
        startTime.valueChanged.connect(lambda x: endTime.setMinimum(x + 0.01))
        startTime.setMaximum(endTime.value())
        endTime.valueChanged.connect(startTime.setMaximum)

        minTime.setMinimumWidth(70)
        minTime.setDecimals(2)
        timer.minTimeChanged.connect(minTime.setValue)
        minTime.valueChanged.connect(timer.setMinTime)
        minTime.setToolTip('Demo start in beats')
        minTime.setStatusTip('Demo start in beats')

        startTime.setMinimumWidth(70)
        startTime.setDecimals(2)
        timer.startChanged.connect(startTime.setValue)
        startTime.valueChanged.connect(timer.setStart)
        startTime.setToolTip('Loop-range start beats')
        startTime.setStatusTip('Loop-range start beats')

        endTime.setMinimumWidth(70)
        endTime.setDecimals(2)
        timer.endChanged.connect(endTime.setValue)
        endTime.valueChanged.connect(timer.setEnd)
        endTime.setToolTip('Loop-range end beats')
        endTime.setStatusTip('Loop-range end beats')

        maxTime.setMinimumWidth(70)
        maxTime.setDecimals(2)
        timer.maxTimeChanged.connect(maxTime.setValue)
        maxTime.valueChanged.connect(timer.setMaxTime)
        maxTime.setToolTip('Demo end in beats')
        maxTime.setStatusTip('Demo end in beats')

        maxTime.setMinimum(minTime.value())
        minTime.valueChanged.connect(maxTime.setMinimum)
        minTime.setMaximum(maxTime.value())
        maxTime.valueChanged.connect(minTime.setMaximum)

        layout.addWidget(minTime)
        layout.addWidget(startTime)
        layout.addWidget(RangeSlider(timer))
        layout.addWidget(endTime)
        layout.addWidget(maxTime)

        isMuted = muteState()
        self.__mute = QPushButton(icons.get('Mute-48') if isMuted else icons.get('Medium Volume-48'), '')
        self.__mute.setToolTip('Un-mute' if isMuted else 'Mute')
        self.__mute.setStatusTip('Un-mute' if isMuted else 'Mute')
        self.__mute.clicked.connect(self.__toggleMute)
        self.__mute.setFixedWidth(24)
        layout.addWidget(self.__mute)

        layout.setStretch(2, 1)

        self.__timer = timer
        goToStart.clicked.connect(self.__seekSoundtrack)
        currentTime.valueChanged.connect(self.__seekSoundtrack)
        timer.timeLooped.connect(self.__seekSoundtrack)
        timeline.valueChanged.connect(self.__seekSoundtrack)

    def __togglePlayPause(self):
        if self.__playPause.toolTip() == 'Play':
            self.__playPause.setIcon(icons.get('Pause-48'))
            self.__playPause.setToolTip('Pause')
            self.__playPause.setStatusTip('Pause')
            self.__playSoundtrack()
        else:
            self.__playPause.setIcon(icons.get('Play-48'))
            self.__playPause.setToolTip('Play')
            self.__playPause.setStatusTip('Play')
            self.__stopSoundtrack()

    def __initSoundtrack(self):
        if muteState():
            return

        if self.__soundtrack:
            return self.__soundtrack

        path = None
        song = None
        for ext in ('.wav', '.mp3'):
            for path in currentProjectDirectory().iter(join=True):
                if not path.hasExt(ext):
                    continue
                try:
                    song = createSong(path)
                except:
                    print ('Found a soundtrack that we could not play. pyglet or mp3 libs missing?\n%s' % e.message)
                    return
                break
            if song:
                break
        if not song:
            return

        self.__soundtrackPath = path
        self.__soundtrack = song
        return self.__soundtrack

    def __seekSoundtrack(self, time):
        if self.__playPause.toolTip() == 'Play':
            # no need to seek when not playing
            # self.__stopSoundtrack()
            return
        if self.__initSoundtrack():
            self.__soundtrack.seekAndPlay(self.__timer.beatsToSeconds(time))

    def __playSoundtrack(self):
        if self.__initSoundtrack():
            self.__soundtrack.seekAndPlay(self.__timer.beatsToSeconds(self.__timer.time))

    def __stopSoundtrack(self):
        if self.__soundtrack:
            self.__soundtrack.stop()

    def __toggleMute(self):
        isMuted = not muteState()
        setMuteState(isMuted)

        self.__mute.setIcon(icons.get('Mute-48') if isMuted else icons.get('Medium Volume-48'))
        self.__mute.setToolTip('Un-mute' if isMuted else 'Mute')
        self.__mute.setStatusTip('Un-mute' if isMuted else 'Mute')

        if self.__soundtrack:  # re-applies the mute state if soundtrack already exists
            # self.__soundtrack.volume = 0 if muteState() else 100
            # play on unmute if already playing
            if self.__timer.isPlaying() and not isMuted:
                self.__soundtrack.seekAndPlay(self.__timer.beatsToSeconds(self.__timer.time))
            else:
                self.__soundtrack.stop()

    def soundtrackPath(self):
        return self.__soundtrackPath
