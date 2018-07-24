from qtutil import *


class KeySelection(QObject):
    changed = pyqtSignal()

    # dict of HermiteKey objects and bitmask of (point, intangent, outtangent)

    def __init__(self):
        super(KeySelection, self).__init__()
        self.__data = {}

    def __repr__(self):
        return str(self.__data)

    def __iter__(self):
        for key in self.__data:
            yield key

    def copy(self):
        return self.__data.copy()

    def clear(self):
        self.__data.clear()

    def get(self, item, fallback):
        return self.__data.get(item, fallback)

    def setdefault(self, item, fallback):
        return self.__data.setdefault(item, fallback)

    def iteritems(self):
        return self.__data.iteritems()

    def iterkeys(self):
        return self.__data.iterkeys()

    def itervalues(self):
        return self.__data.itervalues()

    def __contains__(self, item):
        return item in self.__data

    def __getitem__(self, item):
        return self.__data[item]

    def __setitem__(self, item, value):
        self.__data[item] = value
        self.changed.emit()

    def update(self, other):
        self.__data.update(other)
        self.changed.emit()

    def __delitem__(self, item):
        del self.__data[item]
        self.changed.emit()


# TODO: Mimic maya? when mask is tangent, always deselect key; when selecting, first attempt to select keys, if no keys found then attempt to select tangents
def _select(change, key, existing, mask):
    change[key] = change.setdefault(key, existing) | mask


def _deselect(change, key, existing, mask):
    change[key] = change.setdefault(key, existing) & (~mask)


def selectNew(selection, change, itemsIter):
    # creating new selection, first change is to remove everything
    for key in selection:
        change[key] = 0
    for key, mask in itemsIter:
        # overwrite removed elements with only selected elements
        _select(change, key, selection.get(key, 0), mask)


def selectAdd(selection, change, itemsIter):
    for key, mask in itemsIter:
        # make sure value is new to selection & register for selection
        if key not in selection or not (selection[key] & mask):
            _select(change, key, selection.get(key, 0), mask)


def selectRemove(selection, change, itemsIter):
    for key, mask in itemsIter:
        # make sure value exists in selection & mask out the element to remove
        if key in selection and selection[key] & mask:
            _deselect(change, key, selection[key], mask)


def selectToggle(selection, change, itemsIter):
    for key, mask in itemsIter:
        # make sure value is new to selection & register for selection
        if key not in selection or not (selection[key] & mask):
            _select(change, key, selection.get(key, 0), mask)
        # make sure value exists in selection & mask out the element to remove
        if key in selection and selection[key] & mask:
            _deselect(change, key, selection[key], mask)
