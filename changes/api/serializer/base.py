from collections import defaultdict
from datetime import datetime
from enum import Enum
from uuid import UUID
from typing import cast, Any, Callable, Dict, Generic, Iterator, List, Optional, TypeVar, Tuple, Union  # NOQA

from flask import request

# Types for which serialization is a no-op. Everything boils down to these (or
# to objects without crumblers, which we pass through unscathed)
_PASSTHROUGH = (basestring, bool, int, long, type(None), float)

T = TypeVar('T')


class SerializeTask(Generic[T]):
    class State(Enum):
        # states
        uncalled = 0  # this task hasn't yet been called
        done = 1  # this task is done. Call get() for the result
        depends_on = 2  # finish a list of tasks first, then resume me
        fetch_for = 3  # fetch this data, then send it back to me
        fetched = 4  # the scheduler fetched our data. continue!

    def __init__(self, data):
        # type: (T) -> None
        self.data = data
        self.state = SerializeTask.State.uncalled
        self.result = None  # type: Optional[object]

        self._generator = None  # type: Optional[Iterator[Tuple[SerializeTask.State, Optional[List[SerializeTask[object]]]]]]

    def _run(self):
        # type: () -> Iterator[Tuple[SerializeTask.State, Optional[List[SerializeTask[object]]]]]
        if isinstance(self.data, _PASSTHROUGH):
            yield self._done(self.data)

        elif isinstance(self.data, (list, tuple, set, frozenset)):
            data = cast(Union[list, tuple, set, frozenset], self.data)
            if not isinstance(data, list):
                data = list(data)

            serializer_tasks = {}  # type: Dict[int, SerializeTask[object]]
            for index, item in enumerate(data):
                if isinstance(item, _PASSTHROUGH):
                    continue
                serializer_tasks[index] = SerializeTask(item)

            yield self._depends_on(serializer_tasks.values())
            result = []  # type: List[object]
            for index, item in enumerate(data):
                if index in serializer_tasks:
                    result.append(serializer_tasks[index].get())
                else:
                    result.append(item)
            yield self._done(result)

        elif isinstance(self.data, dict):
            key_serialize_task = SerializeTask(self.data.keys())
            value_serialize_task = SerializeTask(self.data.values())

            yield self._depends_on([key_serialize_task, value_serialize_task])
            yield self._done(dict(zip(key_serialize_task.get(), value_serialize_task.get())))

        else:
            yield self._fetch_for(self.data)
            assert self.state == SerializeTask.State.fetched
            if isinstance(self.fetched, _PASSTHROUGH):
                yield self._done(self.fetched)
                return
            # result might still have dependencies
            serializer_task = SerializeTask(self.fetched)
            yield self._depends_on([serializer_task])
            yield self._done(serializer_task.get())

    def generator(self):
        # type: () -> Iterator[Tuple[SerializeTask.State, Optional[List[SerializeTask[object]]]]]
        if not self._generator:
            self._generator = self._run()
        return self._generator

    def get(self):
        # type: () -> object
        return self.result

    def _done(self, result):
        # type: (object) -> Tuple[SerializeTask.State, Optional[List[SerializeTask[object]]]]
        self.state = SerializeTask.State.done
        self.result = result
        return (self.state, None)

    def _depends_on(self, serialize_task_list):
        # type: (List[SerializeTask]) -> Tuple[SerializeTask.State, List[SerializeTask[object]]]
        self.state = SerializeTask.State.depends_on
        self.dependents = serialize_task_list
        return (self.state, serialize_task_list)

    def _dependents_are_ready(self):
        # type: () -> bool
        return all([task.state == SerializeTask.State.done for task in self.dependents])

    def _fetch_for(self, data):
        # type: (T) -> Tuple[SerializeTask.State, Optional[List[SerializeTask[object]]]]
        self.state = SerializeTask.State.fetch_for
        self.fetchable = data
        return (self.state, None)

    def runnable(self):
        # type: () -> bool
        return (self.state in (SerializeTask.State.uncalled, SerializeTask.State.fetched) or
                (self.state == SerializeTask.State.depends_on and
                 self._dependents_are_ready()))

    def get_fetchable(self):
        # type: () -> object
        return self.fetchable

    def put_fetched(self, fetched):
        # type: (object) -> None
        self.state = SerializeTask.State.fetched
        self.fetched = fetched


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


def new_serialize(data, extended_registry=None):
    # type: (object, Optional[Dict[type, Crumbler[object]]]) -> object
    initial_task = SerializeTask(data)
    all_tasks = [initial_task]

    while initial_task.state != SerializeTask.State.done:
        # our main loop. Basically:
        # - ignore done tasks
        # - if we have any uncalled tasks, tasks that have data ready to use,
        #   or depends_on tasks where all dependents are done, run all of
        #   those tasks for this loop
        # - otherwise we must be stuck on fetch_fors. Do all of the data
        #   fetching
        tasks_to_run = [task for task in all_tasks if task.runnable()]

        if tasks_to_run:
            for task in tasks_to_run:
                result = next(task.generator(), None)
                if result and result[0] == SerializeTask.State.depends_on:
                    all_tasks.extend(result[1])
            continue

        # ok, we must be stuck on fetch_fors. Do all of them
        fetch_tasks = [task for task in all_tasks if task.state == SerializeTask.State.fetch_for]
        fetches_by_class = defaultdict(list)  # type: Dict[type, List[SerializeTask[object]]]

        for f in fetch_tasks:
            fetches_by_class[f.get_fetchable().__class__].append(f)

        for cls, tasks in fetches_by_class.iteritems():
            # we can use the same crumbler object for all items of this type.
            crumbler = get_crumbler(tasks[0].get_fetchable(), extended_registry)
            if crumbler is None:
                # no crumbler for these objects, so just output them directly
                for task in tasks:
                    task.put_fetched(task.get_fetchable())
                continue
            extra_attrs = crumbler.get_extra_attrs_from_db(
                {task.get_fetchable() for task in tasks})
            for task in tasks:
                item = task.get_fetchable()
                task.put_fetched(
                    crumbler.crumble(item, extra_attrs.get(item)))

    return initial_task.get()


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
    if request.args.get('__new_serialize__') == '1':
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
