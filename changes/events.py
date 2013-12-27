from changes.api.base import as_json
from changes.config import pubsub


def publish_job_update(target):
    channels = [
        'jobs:{change_id}:{job_id}'.format(
            change_id=target.change_id.hex if target.change_id else '',
            job_id=target.id.hex,
        ),
        'projects:{project_id}:jobs'.format(
            project_id=target.project_id.hex,
        ),
    ]
    if target.build_id:
        'builds:{build_id}:jobs:{job_id}'.format(
            build_id=target.build_id.hex,
            job_id=target.id.hex,
        )
    if target.author_id:
        channels.append('authors:{author_id}:jobs'.format(
            author_id=target.author_id.hex,
        ))

    if not target.patch_id and target.revision_sha:
        channels.append('revisions:{revision_id}:jobs'.format(
            revision_id=target.revision_sha,
        ))

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
        change_id=target.build.change_id.hex if target.build.change_id else '',
        job_id=target.job_id,
        phase_id=target.id.hex,
    )
    pubsub.publish(channel, {
        'data': as_json(target),
        'event': 'phase.update',
    })


def publish_testgroup_update(target):
    channel = 'testgroups:{job_id}:{testgroup_id}'.format(
        job_id=target.job_id.hex,
        testgroup_id=target.id.hex
    )
    pubsub.publish(channel, {
        'data': as_json(target),
        'event': 'testgroup.update',
    })


def publish_logchunk_update(target):
    channel = 'logsources:{job_id}:{source_id}'.format(
        source_id=target.source_id.hex,
        job_id=target.job_id.hex,
    )
    pubsub.publish(channel, {
        'data': as_json(target),
        'event': 'buildlog.update',
    })
