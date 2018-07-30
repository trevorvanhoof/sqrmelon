from collections import OrderedDict
from qtutil import *
from experiment.modelbase import ItemRow, Label


class Clip(ItemRow):
    def __init__(self, name, loopMode):
        super(Clip, self).__init__(name, loopMode)
        self.__dict__['curves'] = QStandardItemModel()
        self.__dict__['textures'] = OrderedDict()

    @classmethod
    def properties(cls):
        return 'name', 'loopMode'


class Curve(ItemRow):
    def __init__(self, name):
        super(Curve, self).__init__(name)

    @classmethod
    def properties(cls):
        return 'name',


class Event(ItemRow):
    def __init__(self, name, clip, start=0.0, end=1.0, speed=1.0, roll=0.0, track=0):
        super(Event, self).__init__(name, Label(''), clip, start, end, end - start, speed, roll, track)

    def propertyChanged(self, index):
        START_INDEX = 3
        END_INDEX = 4
        DURATION_INDEX = 5

        if index == START_INDEX:
            self.end = self.start + self.duration
        elif index == END_INDEX:
            self.duration = self.end - self.start
        elif index == DURATION_INDEX:
            self.end = self.start + self.duration

    @classmethod
    def properties(cls):
        return 'name', 'scene', 'clip', 'start', 'end', 'duration', 'speed', 'roll', 'track'


class Shot(Event):
    def __init__(self, name, sceneName, clip, start=0.0, end=1.0, speed=1.0, roll=0.0, track=0):
        # intentionally calling super of base
        super(Event, self).__init__(name, Label(sceneName), clip, start, end, end - start, speed, roll, track)
