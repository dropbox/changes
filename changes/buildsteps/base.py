from __future__ import absolute_import

from datetime import datetime

from changes.config import db
from changes.constants import Result, Status
from changes.models import JobStep


class BuildStep(object):
    def can_snapshot(self):
        return False

    def get_label(self):
        raise NotImplementedError

    def execute(self, job):
        """
        Given a new job, execute it (either sync or async), and report the
        results or yield to an update step.
        """
        raise NotImplementedError

    def update(self, job):
        raise NotImplementedError

    def update_step(self, step):
        raise NotImplementedError

    def cancel(self, job):
        # XXX: this makes the assumption that sync_job will take care of
        # propagating the remainder of the metadata
        active_steps = JobStep.query.filter(
            JobStep.job == job,
            JobStep.status != Status.finished,
        )
        for step in active_steps:
            self.cancel_step(step)

            step.status = Status.finished
            step.result = Result.aborted
            step.date_finished = datetime.utcnow()
            db.session.add(step)

        db.session.flush()

    def cancel_step(self, step):
        raise NotImplementedError

    def fetch_artifact(self, artifact):
        raise NotImplementedError

    def expand_jobstep(self, jobstep, new_jobphase, future_jobstep):
        raise NotImplementedError

    def get_allocation_command(self, jobstep):
        raise NotImplementedError
