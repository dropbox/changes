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


# Types for which serialization is a no-op.
_PASSTHROUGH = (basestring, bool, int, long, type(None), float)


def serialize(data, extended_registry=None):
    if extended_registry is None:
        extended_registry = {}

    if isinstance(data, _PASSTHROUGH):
        return data

    if isinstance(data, dict):
        for k, v in data.iteritems():
            if not isinstance(v, _PASSTHROUGH) or not isinstance(k, _PASSTHROUGH):
                # Gotta do it the hard way.
                return dict(zip(serialize(data.keys(), extended_registry),
                                serialize(data.values(), extended_registry)))
        # All keys and values were passthrough, so the dict is already serialized.
        return data

    if isinstance(data, (list, tuple, set, frozenset)):
        if not data:
            return []

        if len(set(type(g) for g in data)) == 1:
            # Make sure it is a list.
            if not isinstance(data, list):
                data = list(data)

            # If we have a list of passthrough, we're done.
            if isinstance(data[0], _PASSTHROUGH):
                return data

            serializer = get_serializer(data[0], extended_registry)

            if serializer:
                attrs = serializer.get_attrs(data)

                data = [serializer(o, attrs=attrs.get(o)) for o in data]

        return [serialize(j, extended_registry) for j in data]

    serializer = get_serializer(data, extended_registry)

    if serializer is None:
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
