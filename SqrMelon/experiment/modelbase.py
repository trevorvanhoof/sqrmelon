from collections import OrderedDict
from experiment.enums import Enum
from qtutil import *
from util import randomColor


class Label(object):
    """ Utiliy to display a non-editable string in the ItemRow system. """

    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


class ItemRow(object):
    """ Represent a row of QStandardItems """

    def __init__(self, name, *args):
        items = [QStandardItem(name)]
        items[0].setData(self)
        self.__dict__['items'] = items
        self.__dict__['color'] = QColor(*randomColor())

        for value in args:
            self.items.append(QStandardItem(str(value)))
            # implicitly cast simple types when getting their values
            # allows direct UI editing as well
            if isinstance(value, (float, int, bool, basestring, Enum)):
                value = type(value)
            # else:
            #    items[-1].setEditable(False)
            items[-1].setData(value)

    @property
    def name(self):
        return self.items[0].text()

    def __getitem__(self, index):
        item = self.items[index]
        if index == 0:
            return item.text()

        data = item.data()

        if isinstance(data, type):
            return data(item.text())

        return data

    def __setitem__(self, index, value):
        item = self.items[index]
        if index == 0:
            item.setText(value)
            return

        item.setText(str(value))

        data = item.data()
        if isinstance(data, type):
            return

        item.setData(value)

    def __str__(self):
        return self.items[0].text()

    @classmethod
    def properties(cls):
        raise NotImplementedError()

    def __getattr__(self, attr):
        try:
            i = self.__class__.properties().index(attr)
        except ValueError:
            raise AttributeError(attr)
        return self[i]

    def __setattr__(self, attr, value):
        try:
            i = self.__class__.properties().index(attr)
        except ValueError:
            raise AttributeError(attr)
        self[i] = value


class Event(ItemRow):
    def __init__(self, name, clip, start=0.0, end=1.0, speed=1.0, roll=0.0):
        super(Event, self).__init__(name, Label(''), clip, start, end, end - start, speed, roll)

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
        return 'name', 'scene', 'clip', 'start', 'end', 'duration', 'speed', 'roll'


class Shot(Event):
    def __init__(self, name, sceneName, clip, start=0.0, end=1.0, speed=1.0, roll=0.0):
        # intentionally calling super of base
        super(Event, self).__init__(name, Label(sceneName), clip, start, end, end - start, speed, roll)


class Clip(ItemRow):
    def __init__(self, name, loopMode):
        super(Clip, self).__init__(name, loopMode)
        self.__dict__['curves'] = OrderedDict()
        self.__dict__['textures'] = OrderedDict()

    @classmethod
    def properties(cls):
        return 'name', 'loopMode'
