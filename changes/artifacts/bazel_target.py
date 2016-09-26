import os

from changes.artifacts.xunit import XunitHandler
from changes.config import db
from changes.constants import ResultSource, Status
from changes.db.utils import get_or_create
from changes.models.bazeltarget import BazelTarget
from changes.models.testresult import TestResultManager
from changes.storage.artifactstore import ARTIFACTSTORE_PREFIX
from changes.utils.agg import aggregate_result


class BazelTargetHandler(XunitHandler):
    FILENAMES = ('test.bazel.xml',)

    def process(self, fp, artifact):
        target_name = self._get_target_name(artifact)
        target, _ = get_or_create(BazelTarget, where={
            'step_id': self.step.id,
            'job_id': self.step.job.id,
            'name': target_name,
            'result_source': ResultSource.from_self,
        })
        test_suites = self.get_test_suites(fp)
        tests = self.aggregate_tests_from_suites(test_suites)
        manager = TestResultManager(self.step, artifact)
        manager.save(tests)

        # update target metadata
        # TODO handle multiple files per target, i.e. sharding and running multiple times
        target.status = Status.finished
        target.result = aggregate_result([t.result for t in tests])
        duration = 0
        for t in test_suites:
            if t.duration is None:
                duration = None
                break
            duration += t.duration
        target.duration = duration
        target.date_created = min([t.date_created for t in test_suites])
        db.session.add(target)
        db.session.commit()
        return tests

    def _get_target_name(self, artifact):
        """Given an artifact, return the target name relative to the root
        of the repo.

        Essentially, we want to go from the artifact name of
        {artifact_store_prefix}foo/bar/baz/test.bazel.xml to
        //foo/bar:baz
        """
        assert artifact.name.startswith(ARTIFACTSTORE_PREFIX)
        path = artifact.name[len(ARTIFACTSTORE_PREFIX):]
        dirname = os.path.dirname(path)
        dirname, target = os.path.split(dirname)
        target = dirname + ':' + target
        return '//' + target.lstrip('/')
