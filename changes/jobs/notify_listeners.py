from changes.jobs.signals import fire_signal
from changes.queue.task import tracked_task


@tracked_task
def notify_job_finished(job_id):
    # TODO(dcramer): remove the use of this task
    fire_signal.delay(
        signal='job.finished',
        kwargs={'job_id': job_id},
    )


@tracked_task
def notify_build_finished(build_id):
    # TODO(dcramer): remove the use of this task
    fire_signal.delay(
        signal='build.finished',
        kwargs={'build_id': build_id},
    )


@tracked_task
def notify_revision_created(repository_id, revision_sha):
    # TODO(dcramer): remove the use of this task
    fire_signal.delay(
        signal='job.finished',
        kwargs={'repository_id': repository_id,
                'revision_sha': revision_sha},
    )
