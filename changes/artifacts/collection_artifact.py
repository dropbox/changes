from __future__ import absolute_import

import json

from changes.config import db
from changes.db.utils import try_create
from changes.models import FailureReason, JobPlan
from changes.utils.http import build_uri
from .base import ArtifactHandler


class CollectionArtifactHandler(ArtifactHandler):
    """
    Base class artifact handler for collection (jobs.json and tests.json) files.

    Does the required job expansion. Subclasses are expected to set
    cls.FILENAMES to the handleable files in question.
    """
    def process(self, fp):
        try:
            phase_config = json.load(fp)
            _, implementation = JobPlan.get_build_step_for_job(job_id=self.step.job_id)
            implementation.expand_jobs(self.step, phase_config)
        except Exception:
            uri = build_uri('/find_build/{0}/'.format(self.step.job.build_id.hex))
            self.logger.warning('Failed to parse json; (step=%s, build=%s)', self.step.id.hex, uri, exc_info=True)
            try_create(FailureReason, {
                'step_id': self.step.id,
                'job_id': self.step.job_id,
                'build_id': self.step.job.build_id,
                'project_id': self.step.project_id,
                'reason': 'malformed_artifact'
            })
            db.session.commit()


class JobsJsonHandler(CollectionArtifactHandler):
    FILENAMES = ('jobs.json',)


class TestsJsonHandler(CollectionArtifactHandler):
    FILENAMES = ('tests.json',)
