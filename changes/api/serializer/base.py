from datetime import datetime
from enum import Enum
from uuid import UUID


# Types for which serialization is a no-op.
_PASSTHROUGH = (basestring, bool, int, long, type(None), float)


def serialize(data, extended_registry=None, use_greedy=False):
    """
    Converts a data structure of dicts, lists, SQLAlchemy objects, and other
    random python objects into something that can be passed to JSON.dumps. This
    is not a guarantee...if data contains an object that we don't know how to
    handle, we'll just leave it in.

    extended_registry: additional Crumblers to use. e.g. one API might
    want to use a special crumbler for Jobs that also adds Build
    information and passes { Job: JobWithBuildCrumbler }

    Its safe (but CPU-expensive) to rerun serialize on data multiple times
    """
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
        # All keys and values were passthrough, so the dict is already
        # serialized.
        return data

    if isinstance(data, (list, tuple, set, frozenset)):
        if not data:
            return []

        # if every item in the list is the same, we want to batch fetch any
        # necessary data from the db before serializing them all
        if len(set(type(g) for g in data)) == 1:
            # Make sure it is a list.
            if not isinstance(data, list):
                data = list(data)

            # If we have a list of passthrough, we're done.
            if isinstance(data[0], _PASSTHROUGH):
                return data

            crumbler = get_crumbler(data[0], extended_registry)

            if crumbler:
                attrs = crumbler.get_extra_attrs_from_db(data)
                data = [crumbler(o, attrs=attrs.get(o)) for o in data]

        return [serialize(j, extended_registry) for j in data]

    # if we're here, we have a single object that we probably need to convert
    # using a crumbler
    crumbler = get_crumbler(data, extended_registry)

    if crumbler is None:
        return data

    attrs = crumbler.get_extra_attrs_from_db([data])
    data = crumbler(data, attrs=attrs.get(data))

    return serialize(data, extended_registry)


#
# Crumbler code: the code that converts SQLAlchemy objects into dictionaries.
# Classes for individual SQLAlchemy objects are in models/
#
# We create a registry of crumblers using class decorators, e.g. use this class
# to convert DateTime objects to strings. serialize() just looks up the right
# class to use and calls it on its objects
#

_registry = {}


def register(type):
    def wrapped(cls):
        _registry[type] = cls()
        return cls
    return wrapped


def get_crumbler(item, registry):
    item_type = type(item)

    crumbler = registry.get(item_type, _registry.get(item_type))

    if crumbler is None:
        for cls, _crumbler in _registry.iteritems():
            if issubclass(item_type, cls):
                crumbler = _crumbler
                break

    return crumbler


class Crumbler(object):
    """
    Converts an object (most often a SQLAlchemy object) to a dict/string/int.
    This is shallow: the returned dict may have values that need to be crumbled
    themselves.

    Why "Crumble"? The name is suggestive of what the class does, and you very likely
    went to these docs to find out more.
    """

    def __call__(self, item, attrs):
        return self.crumble(item, attrs)

    def get_extra_attrs_from_db(self, item_list):
        """
        We may need to do additional data fetching to convert an object: for
        example, we want to look up the phabricator callsign when returning
        revision objects. This function can take a list of objects to crumble
        and returns an attrs dict (object => additional fetched data to use in
        crumble)
        """
        return {}

    def crumble(self, item, attrs):
        """
        Does the actual conversion from object to something simpler. attrs
        should come from get_extra_attrs_from_db, e.g.:

        all_attrs = cls.get_extra_attrs_from_db(item_list)
        s = [cls.crumble(item, all_attrs.get(item)) for item in item_list]
        """
        return {}


@register(datetime)
class DateTimeCrumbler(Crumbler):
    def crumble(self, item, attrs):
        return item.isoformat()


@register(Enum)
class EnumCrumbler(Crumbler):
    def crumble(self, item, attrs):
        return {
            'id': item.name,
            'name': unicode(item),
        }


@register(UUID)
class UUIDCrumbler(Crumbler):
    def crumble(self, item, attrs):
        return item.hex
