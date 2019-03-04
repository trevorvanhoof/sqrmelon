from audioLibs.base import Song
import pyglet


class PyGletSong(Song):
    def __init__(self, path):
        super(PyGletSong, self).__init__(path)
        self.song = None

    def seekAndPlay(self, seconds):
        if self.song is None:
            song = pyglet.media.load(self.path)
            self.song = song.play()
        self.song.seek(seconds)

    def stop(self):
        if self.song is not None:
            self.song.pause()
            self.song = None
