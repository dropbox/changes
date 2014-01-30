from changes.models import Build, Job
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
