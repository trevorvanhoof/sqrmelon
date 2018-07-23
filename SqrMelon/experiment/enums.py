
class Enum(object):
    def __init__(self, label):
        assert label in self.options()
        self.__label = label

    def __str__(self):
        return self.__label

    def index(self):
        return self.options().index(self.__label)

    @staticmethod
    def options():
        raise NotImplementedError()


class ELoopMode(Enum):
    @staticmethod
    def options():
        return 'Clamp', 'Loop'
