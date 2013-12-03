from changes.config import db

from sqlalchemy.exc import IntegrityError


def get_or_create(model, where, defaults=None):
    if defaults is None:
        defaults = {}

    created = False

    instance = model.query.filter_by(**where).limit(1).first()
    if instance is not None:
        return instance, created

    # no one had the lock, so try to create it
    instance = model()
    for key, value in defaults.iteritems():
        setattr(instance, key, value)
    for key, value in where.iteritems():
        setattr(instance, key, value)
    try:
        db.session.add(instance)
    except IntegrityError:
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

    instance = model.query.filter_by(**where).limit(1).first()
    if instance is None:
        instance = model()
        for key, value in values.iteritems():
            setattr(instance, key, value)
        for key, value in where.iteritems():
            setattr(instance, key, value)
        try:
            db.session.add(instance)
        except IntegrityError:
            instance = model.query.filter_by(**where).limit(1).first()
            if instance is None:
                raise Exception('Unable to create or update instance')
            update(instance, values)
            created = False
        else:
            created = True
    else:
        created = False
        update(instance, values)

    return instance, created


def update(instance, values):
    for key, value in values.iteritems():
        if getattr(instance, key) != value:
            setattr(instance, key, value)
    db.session.add(instance)
