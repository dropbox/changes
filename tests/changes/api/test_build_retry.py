from datetime import datetime
from mock import patch, Mock
from changes.constants import Cause, SelectiveTestingPolicy
from changes.models.build import Build
from changes.models.job import Job
from changes.testutils import APITestCase, SAMPLE_DIFF_BYTES
from changes.vcs.base import CommandError, RevisionResult, Vcs, UnknownRevision


class BuildRetryTest(APITestCase):

    def get_fake_vcs(self, log_results=None):
        def _log_results(parent=None, branch=None, offset=0, limit=1):
            assert not branch
            return iter([
                RevisionResult(
                    id='a' * 40,
                    message='hello world',
                    author='Foo <foo@example.com>',
                    author_date=datetime.utcnow(),
                )])
        if log_results is None:
            log_results = _log_results
        # Fake having a VCS and stub the returned commit log
        fake_vcs = Mock(spec=Vcs)
        fake_vcs.read_file.side_effect = CommandError(cmd="test command", retcode=128)
        fake_vcs.exists.return_value = True
        fake_vcs.log.side_effect = UnknownRevision(cmd="test command", retcode=128)
        fake_vcs.export.side_effect = UnknownRevision(cmd="test command", retcode=128)
        fake_vcs.get_changed_files.side_effect = UnknownRevision(cmd="test command", retcode=128)

        def fake_update():
            # this simulates the effect of calling update() on a repo,
            # mainly that `export` and `log` now works.
            fake_vcs.log.side_effect = log_results
            fake_vcs.export.side_effect = None
            fake_vcs.export.return_value = SAMPLE_DIFF_BYTES
            fake_vcs.get_changed_files.side_effect = lambda id: Vcs.get_changed_files(fake_vcs, id)

        fake_vcs.update.side_effect = fake_update

        return fake_vcs

    @patch('changes.models.repository.Repository.get_vcs')
    def test_simple(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
        project = self.create_project()
        build = self.create_build(project=project, selective_testing_policy=SelectiveTestingPolicy.enabled)
        job = self.create_job(build=build)
        self.create_plan(project)

        path = '/api/0/builds/{0}/retry/'.format(build.id.hex)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert data['id']

        new_build = Build.query.get(data['id'])

        assert new_build.id != build.id
        assert new_build.collection_id != build.collection_id
        assert new_build.project_id == project.id
        assert new_build.cause == Cause.retry
        assert new_build.author_id == build.author_id
        assert new_build.source_id == build.source_id
        assert new_build.label == build.label
        assert new_build.message == build.message
        assert new_build.target == build.target
        assert new_build.selective_testing_policy is SelectiveTestingPolicy.disabled

        jobs = list(Job.query.filter(
            Job.build_id == new_build.id,
        ))

        assert len(jobs) == 1

        new_job = jobs[0]
        assert new_job.id != job.id

    @patch('changes.api.build_retry.get_selective_testing_policy')
    @patch('changes.models.repository.Repository.get_vcs')
    def test_with_selective_testing_commit_builds(self, get_vcs, get_selective_testing_policy):
        for policy, reasons, expected_message in [
            (SelectiveTestingPolicy.enabled, ['message1', 'message2'], """
message1
message2
            """.strip()),
            (SelectiveTestingPolicy.enabled, None, None),
            (SelectiveTestingPolicy.disabled, ['message1', 'message2'], """
Selective testing was requested but not done because:
    message1
    message2
            """.strip()),
            (SelectiveTestingPolicy.disabled, None, None),
        ]:
            get_vcs.return_value = self.get_fake_vcs()
            get_selective_testing_policy.return_value = (policy, reasons)
            project = self.create_project()
            build = self.create_build(project=project, selective_testing_policy=SelectiveTestingPolicy.disabled)
            job = self.create_job(build=build)
            self.create_plan(project)

            path = '/api/0/builds/{0}/retry/'.format(build.id.hex)
            resp = self.client.post(path, data={'selective_testing': 'true'}, follow_redirects=True)

            get_selective_testing_policy.assert_called_once_with(project, build.source.revision_sha, None)
            get_selective_testing_policy.reset_mock()

            assert resp.status_code == 200

            data = self.unserialize(resp)

            assert data['id']

            new_build = Build.query.get(data['id'])

            assert new_build.id != build.id
            assert new_build.cause == Cause.retry
            assert new_build.selective_testing_policy is policy

            if expected_message is not None:
                assert len(new_build.messages) == 1
                assert new_build.messages[0].text == expected_message
            else:
                assert len(new_build.messages) == 0

    @patch('changes.models.repository.Repository.get_vcs')
    def test_with_selective_testing_diff_builds(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
        project = self.create_project()
        patch = self.create_patch()
        source = self.create_source(project, patch=patch)
        build = self.create_build(project=project, selective_testing_policy=SelectiveTestingPolicy.disabled, source=source)
        job = self.create_job(build=build)
        self.create_plan(project)

        path = '/api/0/builds/{0}/retry/'.format(build.id.hex)
        resp = self.client.post(path, data={'selective_testing': 'true'}, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert data['id']

        new_build = Build.query.get(data['id'])

        assert new_build.id != build.id
        assert new_build.cause == Cause.retry
        assert new_build.selective_testing_policy is SelectiveTestingPolicy.enabled
