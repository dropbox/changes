import itertools

from changes.config import db

from sqlalchemy.exc import IntegrityError


def try_create(model, where):
    """Try to create an object in the database and return it if successful.
    Args:
        model (Model): DB model class to instantiate.
        where (dict): Values for fields to be populated in the new instance.
    Returns:
        A new instance of the Model if creation was successful, or None if there was a conflict.
    """
    instance = model()
    for key, value in where.iteritems():
        setattr(instance, key, value)
    try:
        with db.session.begin_nested():
            db.session.add(instance)
    except IntegrityError:
        return None
    return instance


def try_update(model, where, values):
    result = db.session.query(type(model)).filter_by(
        **where
    ).update(values, synchronize_session=False)
    return result.rowcount > 0


def _merge_dicts(first, second):
    """Merge two dicts into a new one
    Args:
        first (dict): Primary dict; if a key is present in both, the value from this
            dict is used.
        second (dict): Other dict to merge.
    Returns:
        dict: Union of provided dicts, with value from first used in the case of overlap.
    """
    return {k: v for k, v in itertools.chain(second.iteritems(), first.iteritems())}


def get_or_create(model, where, defaults=None):
    if defaults is None:
        defaults = {}

    created = False

    instance = model.query.filter_by(**where).limit(1).first()
    if instance is not None:
        return instance, created

    instance = try_create(model, _merge_dicts(where, defaults))
    if instance is None:
        instance = model.query.filter_by(**where).limit(1).first()
    else:
        created = True

    if instance is None:
        # this should never happen unless everything is broken
        raise Exception('Unable to get or create instance')

    return instance, created


def create_or_update(model, where, values=None):
    if values is None:
        values = {}

    created = False

    instance = model.query.filter_by(**where).limit(1).first()
    if instance is None:
        instance = try_create(model, _merge_dicts(where, values))
        if instance is None:
            instance = model.query.filter_by(**where).limit(1).first()
            if instance is None:
                raise Exception('Unable to create or update instance')
            _update(instance, values)
        else:
            created = True
    else:
        _update(instance, values)

    return instance, created


def create_or_get(model, where, values=None):
    if values is None:
        values = {}

    created = False

    instance = model.query.filter_by(**where).limit(1).first()
    if instance is None:
        instance = try_create(model, _merge_dicts(where, values))
        if instance is None:
            instance = model.query.filter_by(**where).limit(1).first()
        else:
            created = True

        if instance is None:
            raise Exception('Unable to get or create instance')

    return instance, created


# Not exported because most code should just assign to the properties
# and not create an intermediate dictionary.
def _update(instance, values):
    for key, value in values.iteritems():
        if getattr(instance, key) != value:
            setattr(instance, key, value)
    db.session.add(instance)


def model_repr(*attrs):
    if 'id' not in attrs and 'pk' not in attrs:
        attrs = ('id',) + attrs

    def _repr(self):
        cls = type(self).__name__

        pairs = (
            '%s=%s' % (a, repr(getattr(self, a, None)))
            for a in attrs)

        return u'<%s at 0x%x: %s>' % (cls, id(self), ', '.join(pairs))

    return _repr
