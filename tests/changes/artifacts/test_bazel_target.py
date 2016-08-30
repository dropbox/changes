import mock
import pytest

from cStringIO import StringIO

from changes.artifacts.bazel_target import BazelTargetHandler
from changes.constants import Result, Status
from changes.models.bazeltarget import BazelTarget
from changes.testutils import (
    SAMPLE_XUNIT, SAMPLE_XUNIT_MULTIPLE_SUITES, SAMPLE_XUNIT_MULTIPLE_SUITES_COMPLETE_TIME
)
from changes.testutils.cases import TestCase


@pytest.mark.parametrize('artifact_name, target_name', [
    ('artifactstore/some/path/here/here_test/test.bazel.xml',
     '//some/path/here:here_test'),
    ('artifactstore/some/path/here/target/test.bazel.xml',
     '//some/path/here:target'),
    ('artifactstore/here_test/test.bazel.xml', '//:here_test'),
])
def test_get_target_name(artifact_name, target_name):
    artifact = mock.MagicMock()
    artifact.name = artifact_name
    handler = BazelTargetHandler(None)
    assert handler._get_target_name(artifact) == target_name


class BazelTargetTestCase(TestCase):

    def test_single(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        artifact = self.create_artifact(
            jobstep, 'artifactstore/some/target/target_test/test.bazel.xml')

        handler = BazelTargetHandler(jobstep)

        fp = StringIO(SAMPLE_XUNIT)
        tests = handler.process(fp, artifact)

        target = BazelTarget.query.filter(
            BazelTarget.name == '//some/target:target_test', BazelTarget.step == jobstep).limit(1).first()
        assert target.job == job
        assert target.status is Status.finished
        assert target.result is Result.failed
        assert target.duration == 77
        shas = [t.name_sha for t in target.tests]
        for test_result in tests:
            assert test_result.name_sha in shas
        assert len(tests) == len(target.tests)

    def test_multiple_duration_none(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        artifact = self.create_artifact(
            jobstep, 'artifactstore/some/target/target_test/test.bazel.xml')

        handler = BazelTargetHandler(jobstep)

        fp = StringIO(SAMPLE_XUNIT_MULTIPLE_SUITES)
        tests = handler.process(fp, artifact)

        target = BazelTarget.query.filter(
            BazelTarget.name == '//some/target:target_test', BazelTarget.step == jobstep).limit(1).first()
        assert target.job == job
        assert target.status is Status.finished
        assert target.result is Result.failed
        assert target.duration is None
        shas = [t.name_sha for t in target.tests]
        for test_result in tests:
            assert test_result.name_sha in shas
        assert len(tests) == len(target.tests)

    def test_multiple_duration_complete(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        artifact = self.create_artifact(
            jobstep, 'artifactstore/some/target/target_test/test.bazel.xml')

        handler = BazelTargetHandler(jobstep)

        fp = StringIO(SAMPLE_XUNIT_MULTIPLE_SUITES_COMPLETE_TIME)
        tests = handler.process(fp, artifact)

        target = BazelTarget.query.filter(
            BazelTarget.name == '//some/target:target_test', BazelTarget.step == jobstep).limit(1).first()
        assert target.job == job
        assert target.status is Status.finished
        assert target.result is Result.passed
        assert target.duration == 1577
        shas = [t.name_sha for t in target.tests]
        for test_result in tests:
            assert test_result.name_sha in shas
        assert len(tests) == len(target.tests)
