from changes.api.base import as_json
from changes.config import pubsub


def publish_build_update(mapper, connection, target):
    channel = 'builds:{0}:{1}'.format(target.change.id.hex, target.id.hex)
    pubsub.publish(channel, {
        'data': as_json(target),
        'event': 'build.update',
    })


def publish_change_update(mapper, connection, target):
    channel = 'changes:{0}'.format(target.id.hex)
    pubsub.publish(channel, {
        'data': as_json(target),
        'event': 'change.update',
    })


def publish_phase_update(mapper, connection, target):
    channel = 'phases:{0}:{1}:{2}'.format(
        target.build.change_id.hex, target.build.id.hex, target.id.hex)
    pubsub.publish(channel, {
        'data': as_json(target),
        'event': 'phase.update',
    })
