def create_or_update(session, model, where, values=None):
    if values is None:
        values = {}

    try:
        instance = session.query(model).filter_by(**where)[0]
    except IndexError:
        instance = model()
        for key, value in values.iteritems():
            setattr(instance, key, value)
        for key, value in where.iteritems():
            setattr(instance, key, value)
        session.add(instance)
    else:
        update(session, instance, values)

    return instance


def update(session, instance, values):
    changed = False
    for key, value in values.iteritems():
        if getattr(instance, key) != value:
            setattr(instance, key, value)

    if changed:
        session.add(instance)

    return instance
