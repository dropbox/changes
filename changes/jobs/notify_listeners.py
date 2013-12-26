from changes.models import Job
from changes.signals import SIGNAL_MAP


def notify_listeners(job_id, signal_name):
    job = Job.query.get(job_id)
    if job is None:
        return

    signal = SIGNAL_MAP[signal_name]
    signal.send(job)
