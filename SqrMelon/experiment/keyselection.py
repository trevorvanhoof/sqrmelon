from SqrMelon.experiment.actions import MarqueeActionBase, NestedCommand
from SqrMelon.qtutil import *


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
        self.changed.emit()

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


class KeySelectionEdit(NestedCommand):
    def __init__(self, selectionDict, keyStateDict, parent=None):
        super(KeySelectionEdit, self).__init__('Key selection change', parent)
        self.__selectionModel = selectionDict
        self.__apply = (keyStateDict.copy(), [])

        # move addOrModify actions to remove if we are modifying to '0'
        for key, value in self.__apply[0].iteritems():
            if value == 0:
                # all elements deselected, register for removal
                assert key in self.__selectionModel, 'Attempting to deselect key that wasn\'t selected.'
                self.__apply[1].append(key)

        for key in self.__apply[1]:
            del self.__apply[0][key]

        # cache restore state
        self.__restore = ({}, [])
        for addOrModify in self.__apply[0]:
            if addOrModify in self.__selectionModel:
                # is modification
                self.__restore[0][addOrModify] = self.__selectionModel[addOrModify]
            else:
                self.__restore[1].append(addOrModify)

        for remove in self.__apply[1]:
            self.__restore[0][remove] = self.__selectionModel[remove]

    def redo(self):
        oldState = self.__selectionModel.blockSignals(True)

        self.__selectionModel.update(self.__apply[0])
        for remove in self.__apply[1]:
            del self.__selectionModel[remove]

        self.__selectionModel.blockSignals(oldState)
        if not oldState:
            self.__selectionModel.changed.emit()

    def undo(self):
        oldState = self.__selectionModel.blockSignals(True)

        self.__selectionModel.update(self.__restore[0])
        for remove in self.__restore[1]:
            del self.__selectionModel[remove]

        self.__selectionModel.blockSignals(oldState)
        if not oldState:
            self.__selectionModel.changed.emit()


# TODO: Mimic maya? when mask is tangent, always deselect key; when selecting, first attempt to select keys, if no keys found then attempt to select tangents
def _select(change, key, existing, mask):
    change[key] = change.setdefault(key, existing) | mask


def _deselect(change, key, existing, mask):
    change[key] = change.setdefault(key, existing) & (~mask)


class KeyMarqueeAction(MarqueeActionBase):
    @staticmethod
    def _selectNew(selection, itemsIter):
        # creating new selection, first change is to remove everything
        change = {}
        for key in selection:
            change[key] = 0
        for key, mask in itemsIter:
            # overwrite removed elements with only selected elements
            _select(change, key, selection.get(key, 0), mask)
        return change

    @staticmethod
    def _selectAdd(selection, itemsIter):
        change = {}
        for key, mask in itemsIter:
            # make sure value is new to selection & register for selection
            if key not in selection or not (selection[key] & mask):
                _select(change, key, selection.get(key, 0), mask)
        return change

    @staticmethod
    def _selectRemove(selection, itemsIter):
        change = {}
        for key, mask in itemsIter:
            # make sure value exists in selection & mask out the element to remove
            if key in selection and selection[key] & mask:
                _deselect(change, key, selection[key], mask)
        return change

    @staticmethod
    def _selectToggle(selection, itemsIter):
        change = {}
        for key, mask in itemsIter:
            # make sure value is new to selection & register for selection
            if key not in selection or not (selection[key] & mask):
                _select(change, key, selection.get(key, 0), mask)
            # make sure value exists in selection & mask out the element to remove
            if key in selection and selection[key] & mask:
                _deselect(change, key, selection[key], mask)
        return change

    @staticmethod
    def _createCommand(selection, delta):
        return KeySelectionEdit(selection, delta)
