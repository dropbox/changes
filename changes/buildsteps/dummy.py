from __future__ import absolute_import

from changes.buildsteps.base import BuildStep
from changes.config import db
from changes.constants import Status, Result


class DummyBuildStep(BuildStep):
    def get_label(self):
        return 'do nothing'

    def execute(self, job):
        job.status = Status.finished
        job.result = Result.aborted
        db.session.add(job)

    def update(self, job):
        job.status = Status.finished
        job.result = Result.aborted
        db.session.add(job)

    def update_step(self, step):
        step.status = Status.finished
        step.result = Result.aborted
        db.session.add(step)

    def cancel(self, job):
        job.status = Status.finished
        job.result = Result.aborted
        db.session.add(job)
