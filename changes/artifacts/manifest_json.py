from __future__ import absolute_import

import json

from changes.config import db
from changes.constants import Result
from changes.models import FailureReason
from .base import ArtifactHandler


class ManifestJsonHandler(ArtifactHandler):
    """
    Artifact handler for manifest.json files. Makes sure their contents are valid.
    """
    FILENAMES = ('manifest.json',)

    def process(self, fp):
        try:
            contents = json.load(fp)
            if contents['job_step_id'] != self.step.id.hex:
                self.logger.warning('manifest.json had wrong step id (build=%s): expected %s but got %s',
                                    self.step.job.build_id.hex, self.step.id.hex, contents['job_step_id'])
                self._add_failure_reason()
        except Exception:
            self.logger.warning('Failed to parse manifest.json; (build=%s, step=%s)',
                                self.step.job.build_id.hex, self.step.id.hex, exc_info=True)
            self._add_failure_reason()

    def _add_failure_reason(self):
        db.session.add(FailureReason(
            step_id=self.step.id,
            job_id=self.step.job_id,
            build_id=self.step.job.build_id,
            project_id=self.step.project_id,
            reason='malformed_manifest_json'
        ))
        self.step.result = Result.infra_failed
        db.session.add(self.step)
        db.session.commit()
