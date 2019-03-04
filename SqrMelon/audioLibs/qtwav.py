from qtutil import *
from audioLibs.base import Song
from PyQt4.QtMultimedia import *
import struct


class QtWavSong(Song):
    def __init__(self, path):
        super(QtWavSong, self).__init__(path)
        # parse the file header
        # http://soundfile.sapp.org/doc/WaveFormat/
        with open(path, 'rb') as fh:
            assert fh.read(4) == 'RIFF', 'This is not a wave file'
            fh.read(4)  # file size in bytes, ignore
            assert fh.read(4) == 'WAVE', 'This is not a wave file'
            assert fh.read(4) == 'fmt ', 'This is not a wave file'
            assert struct.unpack('<i', fh.read(4))[0] == 16, 'This is not a PCM wave file, not supported'
            assert struct.unpack('<h', fh.read(2))[0] == 1, 'This is not a PCM wave file, not supported'
            numChannels = struct.unpack('<h', fh.read(2))[0]
            sampleRate = struct.unpack('<i', fh.read(4))[0]
            fh.read(4)  # byteRate
            fh.read(2)  # blockAlign
            bitsPerSample = struct.unpack('<h', fh.read(2))[0]
            assert bitsPerSample in (8, 16)

            assert fh.read(4) == 'data', 'Additional bytes found in PCM wave file header.'
            fh.read(4)  # sample data size
            self.waveDataOffset = fh.tell()  # sample data start

        # store info for seeking
        self.chunkSize = numChannels * bitsPerSample / 8
        self.sampleRate = sampleRate

        # convert to format
        format = QAudioFormat()
        format.setSampleRate(sampleRate)
        format.setChannels(numChannels)
        format.setSampleSize(bitsPerSample)
        format.setCodec("audio/pcm")
        format.setByteOrder(QAudioFormat.LittleEndian)
        # According to the wave format spec the bitsPerSample determins if data is UInt8 or Int16
        format.setSampleType({8: QAudioFormat.UnSignedInt, 16: QAudioFormat.SignedInt}[bitsPerSample])

        # ensure we can play this data
        device = QAudioDeviceInfo.defaultOutputDevice()
        assert device.isFormatSupported(format)

        self.output = QAudioOutput(format, None)
        self.audioFile = QFile(path)
        self.audioFile.open(QIODevice.ReadOnly)
        self.output.start(self.audioFile)

    def seekAndPlay(self, seconds):
        self.audioFile.seek(int(seconds * self.sampleRate) * self.chunkSize + self.waveDataOffset)
        self.output.start(self.audioFile)

    def stop(self):
        self.output.stop()
