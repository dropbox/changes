from __future__ import absolute_import

import json

from changes.config import db
from changes.constants import Result
from changes.models.jobplan import JobPlan
from changes.utils.http import build_web_uri
from .base import ArtifactHandler, ArtifactParseError


class CollectionArtifactHandler(ArtifactHandler):
    """
    Base class artifact handler for collection (jobs.json and tests.json) files.

    Does the required job expansion. Subclasses are expected to set
    cls.FILENAMES to the handleable files in question.
    """
    def process(self, fp, artifact):
        try:
            phase_config = json.load(fp)
        except ValueError:
            uri = build_web_uri('/find_build/{0}/'.format(self.step.job.build_id.hex))
            self.logger.warning('Failed to parse json; (step=%s, build=%s)', self.step.id.hex, uri, exc_info=True)
            self.report_malformed()
        else:
            _, implementation = JobPlan.get_build_step_for_job(job_id=self.step.job_id)
            try:
                implementation.expand_jobs(self.step, phase_config)
            except ArtifactParseError:
                uri = build_web_uri('/find_build/{0}/'.format(self.step.job.build_id.hex))
                self.logger.warning('malformed %s artifact (step=%s, build=%s)', self.FILENAMES[0],
                                    self.step.id.hex, uri, exc_info=True)
                self.report_malformed()
            except Exception:
                uri = build_web_uri('/find_build/{0}/'.format(self.step.job.build_id.hex))
                self.logger.warning('expand_jobs failed (step=%s, build=%s)', self.step.id.hex, uri, exc_info=True)
                self.step.result = Result.infra_failed
                db.session.add(self.step)
                db.session.commit()


class TestsJsonHandler(CollectionArtifactHandler):
    # only match in the root directory
    FILENAMES = ('/tests.json',)
