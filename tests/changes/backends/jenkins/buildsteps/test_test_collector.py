from __future__ import absolute_import

import mock
import responses

from changes.backends.jenkins.generic_builder import JenkinsGenericBuilder
from changes.backends.jenkins.buildsteps.test_collector import JenkinsTestCollectorBuildStep
from changes.constants import Result, Status
from changes.models import JobPhase, JobStep
from changes.testutils import TestCase


class JenkinsTestCollectorBuildStepTest(TestCase):
    def get_buildstep(self):
        return JenkinsTestCollectorBuildStep(
            job_name='foo-bar',
            script='exit 0',
            cluster='default',
            max_shards=2,
        )

    def get_mock_builder(self):
        return mock.Mock(spec=JenkinsGenericBuilder)

    def test_get_builder(self):
        builder = self.get_buildstep().get_builder()
        assert builder.job_name == 'foo-bar'
        assert builder.script == 'exit 0'
        assert builder.cluster == 'default'

    @mock.patch.object(JenkinsTestCollectorBuildStep, 'get_builder')
    def test_default_artifact_handling(self, get_builder):
        builder = self.get_mock_builder()
        get_builder.return_value = builder

        build = self.create_build(self.project)
        job = self.create_job(build, data={
            'job_name': 'server',
            'build_no': '35',
        })
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'item_id': 13,
            'job_name': 'server',
        })
        artifact = {'fileName': 'junit.xml'}

        buildstep = self.get_buildstep()
        buildstep.fetch_artifact(step, artifact)

        builder.sync_artifact.assert_called_once_with(step, artifact)

    def test_get_test_stats(self):
        build = self.create_build(
            project=self.project,
            status=Status.finished,
            result=Result.passed,
        )
        job = self.create_job(build)
        self.create_test(job, name='foo.bar.test_baz', duration=50)
        self.create_test(job, name='foo.bar.test_bar', duration=25)

        buildstep = self.get_buildstep()

        results, avg_time = buildstep.get_test_stats(self.project)

        assert avg_time == 37

        assert results['foo.bar'] == 75
        assert results['foo.bar.test_baz'] == 50
        assert results['foo.bar.test_bar'] == 25

    @responses.activate
    @mock.patch.object(JenkinsTestCollectorBuildStep, 'get_builder')
    @mock.patch.object(JenkinsTestCollectorBuildStep, 'get_test_stats')
    def test_job_expansion(self, get_test_stats, get_builder):
        """
        Fairly heavy integration test which mocks out a few things but ensures
        that generic APIs are called correctly and the tests.json is parsed
        as expected.
        """
        builder = self.get_mock_builder()
        builder.fetch_artifact.return_value.json.return_value = {
            'phase': 'Test',
            'cmd': 'py.test --junit=junit.xml {test_names}',
            'tests': [
                'foo.bar.test_baz',
                'foo.bar.test_bar',
                'foo.bar.test_biz',
                'foo.bar.test_buz',
            ],
        }
        builder.create_job_from_params.return_value = {
            'job_name': 'foo-bar',
            'build_no': 23,
        }

        get_builder.return_value = builder
        get_test_stats.return_value = {
            'foo.bar.test_baz': 50,
            'foo.bar.test_bar': 15,
            'foo.bar.test_biz': 10,
            'foo.bar.test_buz': 200,
            'foo.bar': 275,
        }, 68

        build = self.create_build(self.project)
        job = self.create_job(build, data={
            'job_name': 'server',
            'build_no': '35',
        })
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'item_id': 13,
            'job_name': 'server',
        })
        artifact = {
            'fileName': 'tests.json',
        }

        buildstep = self.get_buildstep()
        buildstep.fetch_artifact(step, artifact)

        phase2 = JobPhase.query.filter(
            JobPhase.job_id == job.id,
            JobPhase.id != phase.id,
        ).first()

        assert phase2, 'phase wasnt created'
        assert phase2.label == 'Test'
        assert phase2.status == Status.queued

        new_steps = sorted(JobStep.query.filter(
            JobStep.phase_id == phase2.id
        ), key=lambda x: x.date_created)

        assert len(new_steps) == 2
        assert new_steps[0].label == '790ed83d37c20fd5178ddb4f20242ef6'
        assert new_steps[0].data == {
            'build_no': 23,
            'job_name': 'foo-bar',
            'tests': ['foo.bar.test_buz'],
            'cmd': 'py.test --junit=junit.xml {test_names}',
        }

        assert new_steps[1].label == '4984ae5173fdb4166e5454d2494a106d'
        assert new_steps[1].data == {
            'build_no': 23,
            'job_name': 'foo-bar',
            'tests': ['foo.bar.test_baz', 'foo.bar.test_bar', 'foo.bar.test_biz'],
            'cmd': 'py.test --junit=junit.xml {test_names}',
        }

        builder.fetch_artifact.assert_called_once_with(step, artifact)
        builder.create_job_from_params.assert_any_call(
            job_name='foo-bar',
            target_id=new_steps[0].id.hex,
            params=builder.get_job_parameters.return_value,
        )
        builder.create_job_from_params.assert_any_call(
            job_name='foo-bar',
            target_id=new_steps[1].id.hex,
            params=builder.get_job_parameters.return_value,
        )
