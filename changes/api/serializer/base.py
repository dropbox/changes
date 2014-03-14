from datetime import datetime
from enum import Enum
from uuid import UUID

_registry = {}


def register(type):
    def wrapped(cls):
        _registry[type] = cls()
        return cls
    return wrapped


def get_serializer(item, registry):
    item_type = type(item)

    serializer = registry.get(item_type, _registry.get(item_type))

    if serializer is None:
        for cls, _serializer in _registry.iteritems():
            if issubclass(item_type, cls):
                serializer = _serializer
                break

    return serializer


def serialize(data, extended_registry=None):
    if extended_registry is None:
        extended_registry = {}

    if data is None:
        return None

    if isinstance(data, (basestring, int, long, float, bool)):
        return data

    if isinstance(data, dict):
        return dict(
            (k, v) for k, v
            in zip(serialize(data.keys(), extended_registry),
                   serialize(data.values(), extended_registry))
        )

    if isinstance(data, (list, tuple, set, frozenset)):
        if not data:
            return []

        if len(set(type(g) for g in data)) == 1:
            data = list(data)

            serializer = get_serializer(data[0], extended_registry)

            if serializer:
                attrs = serializer.get_attrs(data)

                data = [serializer(o, attrs=attrs.get(o)) for o in data]

        return [serialize(j, extended_registry) for j in data]

    serializer = get_serializer(data, extended_registry)

    if serializer is None:
        print 'no serializer', data
        return data

    attrs = serializer.get_attrs([data])

    data = serializer(data, attrs=attrs.get(data))

    return serialize(data, extended_registry)


class Serializer(object):
    def __call__(self, item, attrs):
        return self.serialize(item, attrs)

    def get_attrs(self, item_list):
        return {}

    def serialize(self, item, attrs):
        return {}


@register(datetime)
class DateTimeSerializer(Serializer):
    def serialize(self, item, attrs):
        return item.isoformat()


@register(Enum)
class EnumSerializer(Serializer):
    def serialize(self, item, attrs):
        return {
            'id': item.name,
            'name': unicode(item),
        }


@register(UUID)
class UUIDSerializer(Serializer):
    def serialize(self, item, attrs):
        return item.hex
