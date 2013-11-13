from changes.api.base import as_json
from changes.config import pubsub


def publish_build_update(mapper, connection, target):
    channels = [
        'builds:{change_id}:{build_id}'.format(
            change_id=target.change_id.hex if target.change_id else '',
            build_id=target.id.hex,
        ),
        'projects:{project_id}:builds'.format(
            project_id=target.project_id.hex,
        ),
    ]
    if target.author_id:
        channels.append('authors:{author_id}:builds'.format(
            author_id=target.author_id.hex,
        ))

    for channel in channels:
        json = as_json(target)

        pubsub.publish(channel, {
            'data': json,
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


def publish_testgroup_update(mapper, connection, target):
    channel = 'testgroups:{build_id}:{testgroup_id}'.format(
        build_id=target.build_id.hex,
        testgroup_id=target.id.hex
    )
    pubsub.publish(channel, {
        'data': as_json(target),
        'event': 'testgroup.update',
    })


def publish_logchunk_update(mapper, connection, target):
    channel = 'logsources:{build_id}:{source_id}'.format(
        source_id=target.source_id.hex,
        build_id=target.build_id.hex,
    )
    pubsub.publish(channel, {
        'data': as_json(target),
        'event': 'buildlog.update',
    })
