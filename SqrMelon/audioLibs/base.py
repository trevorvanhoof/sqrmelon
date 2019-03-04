class Song(object):
    def __init__(self, path):
        self.path = path

    def seekAndPlay(self, seconds):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()
