from datetime import datetime

_registry = {}


def register(type):
    def wrapped(cls):
        _registry[type] = cls()
        return cls
    return wrapped


def serialize(item):
    if isinstance(item, (list, tuple, set, frozenset)):
        return [serialize(o) for o in item]
    elif isinstance(item, dict):
        return dict((k, serialize(v)) for k, v in item.iteritems())
    elif item is None:
        return None
    elif isinstance(item, (basestring, int, long, float, bool)):
        return item

    serializer = _registry.get(type(item))
    if serializer:
        return serialize(serializer(item))
    else:
        for cls, serializer in _registry.iteritems():
            if isinstance(item, cls):
                return serialize(serializer(item))
    return item


class Serializer(object):
    def __call__(self, obj):
        return self.serialize(obj)

    def serialize(self, obj):
        return {}


@register(datetime)
class DateTimeSerializer(Serializer):
    def serialize(self, instance):
        return instance.isoformat()
