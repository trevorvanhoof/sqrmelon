import uuid
from collections import OrderedDict


class Serializable(object):
    _instances = []

    def __init__(self, *args, **kwargs):
        Serializable._instances.append(self)
        self.__uuidStr = None
        # initialize with arguments automatically
        if args or kwargs:
            self.initialize(*args, **kwargs)
            self.postInitialize()

    def uuid(self):
        if self.__uuidStr is None:
            self.__uuidStr = str(uuid.uuid4())
        return self.__uuidStr

    def setUuid(self, uuidStr):
        self.__uuidStr = uuidStr

    def initialize(self, *args, **kwargs):
        # substitute for __init__ in case we require constructor with arguments
        raise NotImplementedError()

    def postInitialize(self):
        # called after constructor with initialize or empty constructor with deserialized properties applied
        pass

    @classmethod
    def serializableProperties(cls):
        return
        yield

    def __repr__(self):
        properties = {name: getattr(self, name) for name in self.serializableProperties()}
        return '<Instance of %s, (%s)>' % (self.__class__.__name__, properties)


class AtomSerializable(object):
    """
    Make a type a builtin type (not linked by referenced but by copy, useful for adding e.g. Vector support)
    """

    @classmethod
    def fromAtom(cls, data):
        # used for deserialization
        raise NotImplementedError()

    def toAtom(self):
        # used for serialization
        raise NotImplementedError()


def serializeObjects(instances):
    refIds = OrderedDict()
    queue = instances[:]

    def resolve(obj):
        if obj is None:
            return None
        if isinstance(obj, Serializable):
            if obj in refIds:
                return refIds[obj]
            res = obj.uuid()
            refIds[obj] = obj.uuid()
            queue.append(obj)
            return res
        if isinstance(obj, (tuple, list)):
            return [resolve(o) for o in obj]
        if isinstance(obj, (dict, OrderedDict)):
            res = {k: resolve(o) for k, o in obj.items()}
            for k in res:
                assert isinstance(k, basestring), 'Dictionary contains non-string keys and is not serializable. %s' % obj
            return res
        if isinstance(obj, AtomSerializable):
            obj = obj.toAtom()
        assert isinstance(obj, (int, basestring, float, bool, list, tuple, dict)), 'Object is not JSON serializable. %s' % obj
        return obj

    allData = []
    while queue:
        instance = queue.pop(0)
        instanceData = {'__uuid__': refIds.setdefault(instance, instance.uuid()),
                        '__class__': instance.__class__.__name__}
        for key in instance.serializableProperties():
            if isinstance(key, tuple):
                assert len(key) == 2
                key, typ = key
                assert issubclass(typ, AtomSerializable)
            instanceData[key] = resolve(getattr(instance, key))
        allData.append(instanceData)
    return allData


def serializeAllObjects():
    return serializeObjects(Serializable._instances)


def deserializeObjects(allData):
    # TODO: serializable subclass registry so we can importlib the right dependencies
    def recursiveSubclasses(baseCls):
        for cls in baseCls.__subclasses__():
            for subCls in recursiveSubclasses(cls):
                yield subCls
            yield cls

    factory = {cls.__name__: cls for cls in recursiveSubclasses(Serializable)}

    refIds = {}
    instances = []

    def resolve(obj):
        if isinstance(obj, (tuple, list)):
            return [resolve(o) for o in obj]
        if isinstance(obj, (dict, OrderedDict)):
            return {k: resolve(o) for k, o in obj.items()}
        if obj in refIds:
            return refIds[obj]
        return obj

    # create blank objects and link by UUID
    for instanceData in allData:
        try:
            instance = factory[instanceData['__class__']]()
        except KeyError:
            raise RuntimeError('Error deserializing unknown class %s. Make sure it is imported before deserializing.' % instanceData['__class__'])
        instances.append(instance)
        uuidStr = instanceData['__uuid__']
        refIds[uuidStr] = instance
        instance.setUuid(uuidStr)

    # deserialize data
    for instanceData in allData:
        instance = refIds[instanceData['__uuid__']]
        # silently ignore extra attributes in instanceData by querying the class
        for key in instance.serializableProperties():
            typ = None
            if isinstance(key, tuple):
                assert len(key) == 2
                key, typ = key
                assert issubclass(typ, AtomSerializable)
            # silently ignore not yet serialized properties
            if key not in instanceData:
                continue
            value = instanceData[key]
            # resolve links
            value = resolve(value)
            # process custom atoms
            if typ is not None:
                value = typ.fromAtom(value)
            # set value
            setattr(instance, key, value)

    # call post constructor
    for instanceData in allData:
        instance = refIds[instanceData['__uuid__']]
        instance.postInitialize()

    return instances
