from changes.api.base import as_json
from changes.config import pubsub


def publish_build_update(target):
    channels = [
        'builds:{build_id}'.format(
            build_id=target.id.hex,
        ),
        'projects:{project_id}:builds'.format(
            project_id=target.project.id.hex,
        ),
    ]
    if target.author:
        channels.append('authors:{author_id}:builds'.format(
            author_id=target.author.id.hex,
        ))

    if not target.source.patch and target.source.revision_sha:
        channels.append('revisions:{revision_id}:builds'.format(
            revision_id=target.revision_sha,
        ))

    for channel in channels:
        json = as_json(target)

        pubsub.publish(channel, {
            'data': json,
            'event': 'build.update',
        })


def publish_job_update(target):
    channels = [
        'jobs:{job_id}'.format(
            job_id=target.id.hex,
        ),
        'builds:{build_id}:jobs'.format(
            build_id=target.build.id.hex,
        ),
    ]

    for channel in channels:
        json = as_json(target)

        pubsub.publish(channel, {
            'data': json,
            'event': 'job.update',
        })


def publish_change_update(target):
    channel = 'changes:{0}'.format(target.id.hex)
    pubsub.publish(channel, {
        'data': as_json(target),
        'event': 'change.update',
    })


def publish_phase_update(target):
    channel = 'phases:{change_id}:{job_id}:{phase_id}'.format(
        change_id=target.build.change.id.hex if target.build.change else '',
        job_id=target.job.id.hex,
        phase_id=target.id.hex,
    )
    pubsub.publish(channel, {
        'data': as_json(target),
        'event': 'phase.update',
    })


def publish_testgroup_update(target):
    channel = 'testgroups:{job_id}:{testgroup_id}'.format(
        job_id=target.job.id.hex,
        testgroup_id=target.id.hex
    )
    pubsub.publish(channel, {
        'data': as_json(target),
        'event': 'testgroup.update',
    })


def publish_logchunk_update(target):
    channel = 'logsources:{job_id}:{source_id}'.format(
        source_id=target.source.id.hex,
        job_id=target.job.id.hex,
    )
    pubsub.publish(channel, {
        'data': as_json(target),
        'event': 'buildlog.update',
    })
