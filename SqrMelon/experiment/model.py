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


class Event(ItemRow):
    def __init__(self, name, clip, start=0.0, end=1.0, speed=1.0, roll=0.0, track=0):
        super(Event, self).__init__(name, clip, start, end, end - start, speed, roll, track)

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
        return 'name', 'clip', 'start', 'end', 'duration', 'speed', 'roll', 'track'


class Shot(ItemRow):
    def __init__(self, name, sceneName, start=0.0, end=1.0, track=0):
        super(Shot, self).__init__(name, Label(sceneName), start, end, end - start, track)

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
        return 'name', 'scene', 'start', 'end', 'duration', 'track'
