from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class Song:
    def __init__(self, path: str) -> None:
        self.path = path
        self._player = QMediaPlayer()
        self._audioOutput = QAudioOutput()
        self._player.setAudioOutput(self._audioOutput)
        self._player.setSource(path)
        self._audioOutput.setVolume(100)
        assert self._player.isSeekable()

    def seekAndPlay(self, seconds: float) -> None:
        self._player.setPosition(int(seconds * 1000))
        self._player.play()

    def stop(self) -> None:
        self._player.stop()
