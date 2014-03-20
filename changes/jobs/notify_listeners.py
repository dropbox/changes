from changes.models import Build, Job, Revision
from changes.signals import SIGNAL_MAP


def notify_job_finished(job_id):
    job = Job.query.get(job_id)
    if job is None:
        return

    signal = SIGNAL_MAP['job.finished']
    signal.send_robust(job)


def notify_build_finished(build_id):
    build = Build.query.get(build_id)
    if build is None:
        return

    signal = SIGNAL_MAP['build.finished']
    signal.send_robust(build)


def notify_revision_created(repository_id, revision_sha):
    revision = Revision.query.filter(
        Revision.repository_id == repository_id,
        Revision.sha == revision_sha,
    ).first()
    if revision is None:
        return

    signal = SIGNAL_MAP['revision.created']
    signal.send_robust(revision)
