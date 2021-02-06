from pycompat import *
from qtutil import *
from audioLibs.base import Song

try:
    from PyQt4.phonon import Phonon
except ImportError:
    try:
        from PyQt5.phonon import Phonon
    except ImportError:
        try:
            from PySide.phonon import Phonon
        except ImportError:
            from PySide2.phonon import Phonon


class PhononSong(Song):
    # fallback for when pyglet doesn't work
    def __init__(self, path):
        super(PhononSong, self).__init__(path)

        self.player = Phonon.MediaObject()
        self.output = Phonon.AudioOutput(Phonon.MusicCategory, None)
        Phonon.createPath(self.player, self.output)
        self.song = Phonon.MediaSource(path)
        self.player.setCurrentSource(self.song)
        self.tick = None
        self.player.stateChanged.connect(self.__doSeek)

    def __doSeek(self, state, __s):
        if self.tick is None:
            return
        if state == Phonon.PlayingState:
            self.player.seek(self.tick)
            self.tick = None

    def seekAndPlay(self, seconds):
        self.player.play()
        # seek silently fails if we're still buffering or loading
        # so let's store what to seek for later if that's the case
        if self.player.state() != Phonon.PlayingState:
            self.tick = long(seconds * 1000)
            return
        self.player.seek(long(seconds * 1000))

    def stop(self):
        self.player.stop()
