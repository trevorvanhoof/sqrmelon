def createSong(path):
    # Try to play a song

    try:
        # QtMultimedia comes for free, but it only supports wave files
        # will throw an error if file format is not understood
        from qtwav import QtWavSong
        return QtWavSong(path)
    except ImportError:
        pass

    try:
        # PyGlet only handles mp3s if lib avbin is installed
        # also newer versions than 1.3.2 are not functioning.
        # We couldn't get it to work on linux.
        from glet import PyGletSong
        return PyGletSong(path)
    except ImportError:
        pass

    try:
        # Qt4 Phonon has a timing issue, essentially the song appears slowed down
        # it is the most robust playback we found, but it's plain wrong.
        from phonon import PhononSong
        return PhononSong(path)
    except ImportError:
        pass
