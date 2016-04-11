from collections import defaultdict
from datetime import datetime
from enum import Enum
from uuid import UUID
from typing import cast, Any, Callable, Dict, Generic, Iterable, List, Optional, TypeVar  # NOQA
from itertools import izip

from flask import request

# Types for which serialization is a no-op. Everything boils down to these (or
# to objects without crumblers, which we pass through unscathed)
_PASSTHROUGH = (basestring, bool, int, long, type(None), float)

T = TypeVar('T')


class Future(object):
    __slots__ = ('data', 'final')

    def __init__(self, data, final=None):
        # type: (object, object) -> None
        self.data = data
        self.final = final


def old_serialize(data, extended_registry=None):
    if extended_registry is None:
        extended_registry = {}

    if isinstance(data, _PASSTHROUGH):
        return data

    if isinstance(data, dict):
        for k, v in data.iteritems():
            if not isinstance(v, _PASSTHROUGH) or not isinstance(k, _PASSTHROUGH):
                # Gotta do it the hard way.
                return dict(zip(old_serialize(data.keys(), extended_registry),
                                old_serialize(data.values(), extended_registry)))
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

        return [old_serialize(j, extended_registry) for j in data]

    # if we're here, we have a single object that we probably need to convert
    # using a crumbler
    crumbler = get_crumbler(data, extended_registry)

    if crumbler is None:
        return data

    attrs = crumbler.get_extra_attrs_from_db([data])
    data = crumbler(data, attrs=attrs.get(data))

    return old_serialize(data, extended_registry)


def _gather(data, collected):
    # type: (object, List[Future]) -> object
    """
    Crawls `data`, and returns an equivalent structure where any non-serializable
    objects are replaced with Future objects, to be filled in later.

    Args:
        data: the data to crawl
        collected: list which is populated with the Future
            objects this method generates
    Returns:
        An object with the same structure as `data`, but with any
        non-serializable objects replaced with Future objects.
    """
    if isinstance(data, _PASSTHROUGH):
        return data

    elif isinstance(data, dict):
        # optimize for the case that keys are strings
        keys = [k if isinstance(k, _PASSTHROUGH) else _gather(k, collected)
                for k in data.iterkeys()]
        values = [_gather(v, collected) for v in data.itervalues()]
        return dict(izip(keys, values))

    elif isinstance(data, (list, tuple, set, frozenset)):
        data = cast(Iterable, data)
        return [_gather(item, collected) for item in data]

    else:
        # need to crumble this.
        future = Future(data=data)
        collected.append(future)
        return future


def _finalize_futures(needs_crumble, extended_registry):
    # type: (List[Future], Optional[Dict[type, Crumbler[object]]]) -> None
    """
    Given a list of Future objects that need to be crumbled, crumbles them,
    and then recursively gathers and crumbles the results of the Future
    objects' crumbling. Puts off crumbling until an entire layer of objects has
    been collected, so that we can do `get_extra_attrs_from_db` for many objects
    at a time.

    Args:
        needs_crumble: list of initial Future objects to be crumbled
        extended_registry: additional crumblers to use for this serialization
    """
    while needs_crumble:
        fetches_by_class = defaultdict(list)  # type: Dict[type, List[Future]]
        for future in needs_crumble:
            fetches_by_class[future.data.__class__].append(future)

        needs_crumble = []
        for cls, futures in fetches_by_class.iteritems():
            # we can use the same crumbler object for all items of this type.
            crumbler = get_crumbler(futures[0].data, extended_registry)
            if crumbler is None:
                # no crumbler for these objects, so just output them directly
                for future in futures:
                    future.final = future.data
                continue
            extra_attrs = crumbler.get_extra_attrs_from_db(
                {future.data for future in futures})
            for future in futures:
                item = future.data
                crumbled = crumbler.crumble(item, extra_attrs.get(item))
                future.final = _gather(crumbled, needs_crumble)


def _expand(data):
    # type: (object) -> object
    """
    Final step of serialization. Given `data`, a structure that contains
    finalized `Future` objects, returns an equivalent structure where the
    `Future` objects are replaced with their finalized (crumbled) value.
    May mutate `data` in some cases.
    """
    if isinstance(data, _PASSTHROUGH):
        return data

    elif isinstance(data, dict):
        # since we created this dict, it's safe for us to just mutate it,
        # which avoids doing a zip.
        for k, v in data.iteritems():
            # usually keys are just strings, so we optimize for that case
            if isinstance(k, _PASSTHROUGH):
                data[k] = _expand(v)
            else:
                # mutating a dict while iterating is tricky, and we
                # don't expect to hit this case often, so we just create a new
                # dict in this case
                keys = [_expand(k) for k in data.iterkeys()]
                # we might be calling _expand a second time if we'd already
                # iterated over this key-value pair before finding a
                # non-trivial key, but expansion is idempotent so we're okay.
                values = [_expand(v) for v in data.itervalues()]
                return dict(izip(keys, values))
        return data

    elif isinstance(data, list):
        return [_expand(item) for item in data]

    elif isinstance(data, Future):
        return _expand(data.final)

    else:
        # data for which we have no crumbler
        return data


def new_serialize(data, extended_registry=None):
    # type: (object, Optional[Dict[type, Crumbler[object]]]) -> object
    needs_crumble = []  # type: List[Future]
    initial = _gather(data, needs_crumble)
    if not needs_crumble:
        return initial

    _finalize_futures(needs_crumble, extended_registry)

    # everything should be fully crumbled now, just have to assemble it
    return _expand(initial)


def serialize(data, extended_registry=None):
    # type: (object, Optional[Dict[type, Crumbler[object]]]) -> object
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
    if request.args.get('__new_serialize__', '1') == '1':
        return new_serialize(data, extended_registry)
    else:
        return old_serialize(data, extended_registry)


#
# Crumbler code: the code that converts SQLAlchemy objects into dictionaries.
# Classes for individual SQLAlchemy objects are in models/
#
# We create a registry of crumblers using class decorators, e.g. use this class
# to convert DateTime objects to strings. serialize() just looks up the right
# class to use and calls it on its objects
#

_registry = {}  # type: Dict[type, Crumbler[object]]


def register(type):
    # type: (type) -> Callable[[type], type]
    def wrapped(cls):
        _registry[type] = cls()
        return cls
    return wrapped


def get_crumbler(item, registry):
    # type: (T, Optional[Dict[type, Crumbler[object]]]) -> Crumbler[T]
    item_type = type(item)  # type: ignore

    crumbler = None
    if registry:
        crumbler = registry.get(item_type)
    if crumbler is None:
        crumbler = _registry.get(item_type)

    if crumbler is None:
        for cls, _crumbler in _registry.iteritems():
            # XXX(nate): issubclass doesn't seem that safe. We aren't iterating
            # in a fixed order.
            if issubclass(item_type, cls):
                crumbler = _crumbler
                break

    return cast(Crumbler[T], crumbler)


# TODO(nate): these methods should all just be made static.
class Crumbler(Generic[T]):
    """
    Converts an object (most often a SQLAlchemy object) to a dict/string/int.
    This is shallow: the returned dict may have values that need to be crumbled
    themselves.

    Why "Crumble"? The name is suggestive of what the class does, and you very likely
    went to these docs to find out more.
    """

    def __call__(self, item, attrs):
        # type: (T, Dict[str, Any]) -> object
        return self.crumble(item, attrs)

    def get_extra_attrs_from_db(self, item_set):
        # type: (Set[T]) -> Dict[T, Dict[str, Any]]
        """
        We may need to do additional data fetching to convert an object: for
        example, we want to look up the phabricator callsign when returning
        revision objects. This function can take a set of objects to crumble
        and returns an attrs dict (object => dict of fetched data for use
        in `crumble`)
        """
        return {}

    def crumble(self, item, attrs):
        # type: (T, Dict[str, Any]) -> object
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
