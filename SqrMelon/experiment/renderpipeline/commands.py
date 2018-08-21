from qtutil import *
from model import Plug


class MoveNode(QUndoCommand):
    def __init__(self, node, oldPos, callback, parent=None):
        super(MoveNode, self).__init__('Node moved', parent)
        self.__node = node
        self.__oldPos = oldPos
        self.__newPos = self.__node.x, self.__node.y
        self.__applied = True
        self.__callback = callback

    def redo(self):
        if self.__applied:
            return
        self.__applied = True
        self.__node.setPosition(*self.__newPos)
        self.__callback()

    def undo(self):
        self.__applied = False
        self.__node.setPosition(*self.__oldPos)
        self.__callback()


class AddNode(QUndoCommand):
    def __init__(self, graph, node, triggerRepaint):
        super(AddNode, self).__init__('Add node')
        self.__graph = graph
        self.__node = node
        self.__triggerRepaint = triggerRepaint

    def redo(self):
        self.__graph.append(self.__node)
        self.__triggerRepaint()

    def undo(self):
        self.__graph.remove(self.__node)
        self.__triggerRepaint()


class DeleteNode(QUndoCommand):
    def __init__(self, graph, node, triggerRepaint):
        super(DeleteNode, self).__init__('Delete node')
        self.__graph = graph
        self.__node = node
        self.__triggerRepaint = triggerRepaint

    def redo(self):
        self.__graph.remove(self.__node)
        self.__triggerRepaint()

    def undo(self):
        self.__graph.append(self.__node)
        self.__triggerRepaint()


class ConnectionEdit(QUndoCommand):
    def __init__(self, a, b, triggerRepaint, parent=None):
        super(ConnectionEdit, self).__init__('Connection edit', parent)
        self._triggerRepaint = triggerRepaint
        self._connect = None
        self._disconnect = tuple()
        if a in a.node.inputs:
            if b is None:  # break connections to a
                self._disconnect = tuple((c, a) for c in a.connections)
            else:
                self._connect = b, a
                # disconnect other inputs from a
                self._disconnect = tuple((c, a) for c in a.connections)
        elif b is not None:  # connect b to a
            self._connect = a, b  # connect a to b
            # disconnect other inputs from b
            self._disconnect = tuple((c, b) for c in b.connections)

    def redo(self):
        if self._connect is not None:
            a, b = self._connect
            a.connections.append(b)
            b.connections.append(a)
        for a, b in self._disconnect:
            a.connections.remove(b)
            b.connections.remove(a)
        self._triggerRepaint()

    def undo(self):
        for a, b in self._disconnect:
            a.connections.append(b)
            b.connections.append(a)
        if self._connect is not None:
            a, b = self._connect
            a.connections.remove(b)
            b.connections.remove(a)
        self._triggerRepaint()


class SetAttr(QUndoCommand):
    def __init__(self, setter, restoreValue, newValue, callback, parent=None):
        super(SetAttr, self).__init__('Attribute change', parent)
        self._setter = setter
        self._newValue = newValue
        self._restoreValue = restoreValue
        self._callback = callback

    def redo(self):
        self._setter(self._newValue)
        self._callback()

    def undo(self):
        self._setter(self._restoreValue)
        self._callback()


class NodeEditArray(QUndoCommand):
    Add = True
    Remove = False

    def __init__(self, inspect, array, node, elements, mode, callback, parent=None):
        super(NodeEditArray, self).__init__('Node element add/remove', parent)
        self._inspect = inspect
        self._array = array
        self._node = node
        self._elements = elements
        self._mode = mode
        self._callback = callback

    def redo(self):
        if self._mode == NodeEditArray.Add:
            self._array.extend(self._elements)
        else:
            for element in self._elements:
                self._array.remove(element)
                if isinstance(element, Plug):
                    # clear connections to this plug
                    for entry in element.connections:
                        entry.connections.remove(element)
        self._inspect(self._node)
        self._node.layout()
        self._callback()

    def undo(self):
        if self._mode == NodeEditArray.Add:
            for element in self._elements:
                self._array.remove(element)
        else:
            # TODO: reinsert at right indices, undo/redo now shuffles plugs. It doesn't break but it's confusing to the user.
            self._array.extend(self._elements)
            for element in self._elements:
                if isinstance(element, Plug):
                    # restore connections to this plug
                    for entry in element.connections:
                        entry.connections.append(element)
        self._inspect(self._node)
        self._node.layout()
        self._callback()
