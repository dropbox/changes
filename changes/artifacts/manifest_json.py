from __future__ import absolute_import

import json

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
        except Exception:
            self.logger.exception('Failed to parse manifest.json; (build=%s, step=%s)',
                                self.step.job.build_id.hex, self.step.id.hex)
