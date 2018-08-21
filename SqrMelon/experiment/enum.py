from serializable import AtomSerializable


class Enum(AtomSerializable):
    def __init__(self, label):
        if isinstance(label, basestring):
            assert label in self.options()
            self.__value = self.options().index(label)
            self.__label = label
        else:
            assert isinstance(label, int)
            assert 0 <= label < len(self.options())
            self.__value = label
            self.__label = self.options()[label]

    def __eq__(self, other):
        return self.__value == other.__value

    def __ne__(self, other):
        return self.__value != other.__value

    def __str__(self):
        return self.__label

    def index(self):
        return self.__value

    @staticmethod
    def options():
        raise NotImplementedError()

    @classmethod
    def fromAtom(cls, data):
        return cls(data)

    def toAtom(self):
        return self.__label
