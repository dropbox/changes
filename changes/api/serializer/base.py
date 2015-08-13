from datetime import datetime
from enum import Enum
from uuid import UUID
from flask import request

# This is somewhat :(
#
# So we've already batched the database fetches for a bunch of sqlalchemy
# objects together. These objects probably have joins/joinedloads, though,
# which may also need to do data fetches (and/or have joins themselves that
# have data fetches.) Without the function you're reading about now, those
# would all happen serially.
#
# So here's what we'll do. We'll write a function that operates on a list of
# already-converted dictionaries (from a Crumbler.) We can
# find every key/value pair within that dict that has its own data fetching to
# do [1], batch all of that data fetching together and crumble those objects.
# Now we can recursively run ourselves on that resulting list, and replace
# the original value with the final result from this greedy fetch.
#
# Another way of describing this is that we do a depth first search and crumble
# everything we come across, transforming the original structure in place.
#
# [1] The implmentation does this for every value that has its own Crumble object
# even if get_extra_attrs_from_db is a no-op
#
# Based on the way serialization is written, this cannot change what we'd
# output... we're basically allowed to run object_to_dict on objects whenever
# we want, as long as we make sure to run serialize on them afterwards. In this
# case, the caller of this function will run serialize on this entire tree
# after we're done.
#
# Philosophically, this function is written so that running it can only make
# things better: there may be corner cases where it fails to batch something
# that should be batched, but if it fails that won't break anything
#
# @param (data): a list of objects that have already had serializer run on them


def greedily_try_to_batch_data_fetches(data, extended_registry):
    # we only care about lists of dicts
    if not isinstance(data, list) or not isinstance(data[0], dict):
        return data

    for k in data[0].keys():
        if isinstance(data[0][k], _PASSTHROUGH):
            # cheap check to see if value is boring before calling
            # get_crumbler
            continue

        crumbler = get_crumbler(data[0][k], extended_registry)
        if not crumbler:
            # this isn't a key that might do data fetching
            continue

        objs_to_crumble = [o[k] for o in data]

        # let's double check that all of these objects are the same type
        # (missing objects/None values are ok)
        if len(set(type(o) for o in objs_to_crumble if o)) != 1:
            continue

        # ok, batch the data fetch for all of these child keys and run
        # serializer
        attrs = crumbler.get_extra_attrs_from_db(objs_to_crumble)
        replacements = [crumbler(o, attrs=attrs.get(o)) if o else None
                        for o in objs_to_crumble]

        # we've serialized the child data fetch. But it might also have
        # children that want to fetch data, so let's recursively call greed!
        if isinstance(replacements[0], dict):
            replacements = greedily_try_to_batch_data_fetches(replacements,
                                                              extended_registry)

        # replace the originals with our fetched&crumbled objects
        replacement_dict = dict(zip(objs_to_crumble, replacements))
        for o in data:
            if o[k] in replacement_dict:
                o[k] = replacement_dict[o[k]]
    return data

# Types for which serialization is a no-op.
_PASSTHROUGH = (basestring, bool, int, long, type(None), float)


def serialize(data, extended_registry=None):
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

                disable_greedy_batching = int(request.args.get('__nobatch__', 0))
                if not disable_greedy_batching:
                    greedily_try_to_batch_data_fetches(data, extended_registry)

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
