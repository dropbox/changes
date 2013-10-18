from changes.api.base import as_json
from changes.config import pubsub


def publish_build_update(mapper, connection, target):
    channel = 'builds:{change_id}:{build_id}'.format(
        change_id=target.change_id.hex if target.change_id else '',
        build_id=target.id.hex,
    )
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
    channel = 'phases:{change_id}:{build_id}:{phase_id}'.format(
        change_id=target.build.change_id.hex if target.build.change_id else '',
        build_id=target.build_id,
        phase_id=target.id.hex,
    )
    pubsub.publish(channel, {
        'data': as_json(target),
        'event': 'phase.update',
    })


def publish_test_update(mapper, connection, target):
    channel = 'tests::{build_id}:{test_id}'.format(
        build_id=target.build_id.hex,
        test_id=target.id.hex
    )
    pubsub.publish(channel, {
        'data': as_json(target),
        'event': 'test.update',
    })
