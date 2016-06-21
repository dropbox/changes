import mock
import yaml

from datetime import datetime

from changes.config import db
from changes.constants import Cause, Result, Status
from changes.models.build import Build
from changes.models.job import Job
from changes.models.project import ProjectOption
from changes.testutils import APITestCase, SAMPLE_DIFF, SAMPLE_DIFF_BYTES
from changes.vcs.base import CommandError, InvalidDiffError, RevisionResult, UnknownRevision, Vcs


class DiffBuildRetryTest(APITestCase):

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
        fake_vcs = mock.Mock(spec=Vcs)
        fake_vcs.read_file.side_effect = CommandError(
            cmd="test command", retcode=128)
        fake_vcs.exists.return_value = True
        fake_vcs.log.side_effect = UnknownRevision(
            cmd="test command", retcode=128)
        fake_vcs.export.side_effect = UnknownRevision(
            cmd="test command", retcode=128)
        fake_vcs.get_patch_hash.return_value = 'a' * 40

        def fake_update():
            # this simulates the effect of calling update() on a repo,
            # mainly that `export` and `log` now works.
            fake_vcs.log.side_effect = log_results
            fake_vcs.export.side_effect = None
            fake_vcs.export.return_value = SAMPLE_DIFF_BYTES

        fake_vcs.update.side_effect = fake_update

        return fake_vcs

    def setUp(self):
        super(DiffBuildRetryTest, self).setUp()
        diff_id = 123
        self.project = self.create_project()
        self.patch = self.create_patch(
            repository_id=self.project.repository_id,
            diff=SAMPLE_DIFF
        )
        self.source = self.create_source(
            self.project,
            patch=self.patch,
        )
        self.diff = self.create_diff(diff_id, source=self.source)
        self.create_plan(self.project)

    @mock.patch('changes.models.repository.Repository.get_vcs')
    def test_simple(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
        build = self.create_build(
            project=self.project,
            source=self.source,
            status=Status.finished,
            result=Result.failed
        )
        job = self.create_job(build=build)

        path = '/api/0/phabricator_diffs/{0}/retry/'.format(self.diff.diff_id)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert len(data) == 1

        new_build = Build.query.get(data[0]['id'])

        assert new_build.id != build.id
        assert new_build.collection_id != build.collection_id
        assert new_build.project_id == self.project.id
        assert new_build.cause == Cause.retry
        assert new_build.author_id == build.author_id
        assert new_build.source_id == build.source_id
        assert new_build.label == build.label
        assert new_build.message == build.message
        assert new_build.target == build.target

        (new_job,) = list(Job.query.filter(
            Job.build_id == new_build.id,
        ))
        assert new_job.id != job.id

    @mock.patch('changes.models.repository.Repository.get_vcs')
    def test_simple_multiple_diffs(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
        self.create_diff(124, source=self.source)
        build = self.create_build(
            project=self.project,
            source=self.source,
            status=Status.finished,
            result=Result.failed
        )
        job = self.create_job(build=build)

        path = '/api/0/phabricator_diffs/{0}/retry/'.format(self.diff.diff_id)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert len(data) == 1

        new_build = Build.query.get(data[0]['id'])

        assert new_build.id != build.id
        assert new_build.collection_id != build.collection_id
        assert new_build.project_id == build.project_id
        assert new_build.source_id == build.source_id

        (new_job,) = list(Job.query.filter(
            Job.build_id == new_build.id,
        ))
        assert new_job.id != job.id

    @mock.patch('changes.models.repository.Repository.get_vcs')
    def test_simple_passed(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
        build = self.create_build(
            project=self.project,
            source=self.source,
            status=Status.finished,
            result=Result.passed
        )
        self.create_job(build=build)

        path = '/api/0/phabricator_diffs/{0}/retry/'.format(self.diff.diff_id)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert len(data) == 0

    @mock.patch('changes.models.repository.Repository.get_vcs')
    def test_simple_in_progress(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
        build = self.create_build(
            project=self.project,
            source=self.source,
            status=Status.in_progress,
            result=Result.failed
        )
        self.create_job(build=build)

        path = '/api/0/phabricator_diffs/{0}/retry/'.format(self.diff.diff_id)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert len(data) == 0

    @mock.patch('changes.models.repository.Repository.get_vcs')
    def test_multiple_builds_same_project(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
        self.create_build(
            project=self.project,
            source=self.source
        )
        build = self.create_build(
            project=self.project,
            source=self.source,
            status=Status.finished,
            result=Result.failed
        )
        job = self.create_job(build=build)

        path = '/api/0/phabricator_diffs/{0}/retry/'.format(self.diff.diff_id)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert len(data) == 1

        new_build = Build.query.get(data[0]['id'])

        assert new_build.id != build.id
        assert new_build.collection_id != build.collection_id
        assert new_build.project_id == self.project.id
        assert new_build.source_id == build.source_id

        (new_job,) = list(Job.query.filter(
            Job.build_id == new_build.id,
        ))
        assert new_job.id != job.id

    @mock.patch('changes.models.repository.Repository.get_vcs')
    def test_multiple_builds_different_projects(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
        self.create_build(
            project=self.project,
            source=self.source
        )
        build = self.create_build(
            project=self.project,
            source=self.source,
            status=Status.finished,
            result=Result.failed
        )
        job = self.create_job(build=build)

        project2 = self.create_project(
            repository=self.project.repository,
            name="project 2"
        )

        build2 = self.create_build(
            project=project2,
            source=self.source,
            status=Status.finished,
            result=Result.passed
        )

        self.create_job(build=build2)

        self.create_plan(project2)

        path = '/api/0/phabricator_diffs/{0}/retry/'.format(self.diff.diff_id)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert len(data) == 1

        new_build = Build.query.get(data[0]['id'])

        assert new_build.id != build.id
        assert new_build.collection_id != build.collection_id
        assert new_build.project_id == self.project.id
        assert new_build.source_id == build.source_id

        (new_job,) = list(Job.query.filter(
            Job.build_id == new_build.id,
        ))
        assert new_job.id != job.id

    @mock.patch('changes.models.repository.Repository.get_vcs')
    def test_multiple_builds_different_projects_all_failed(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
        self.create_build(
            project=self.project,
            source=self.source
        )
        build = self.create_build(
            project=self.project,
            source=self.source,
            status=Status.finished,
            result=Result.failed
        )
        job = self.create_job(build=build)

        project2 = self.create_project(
            repository=self.project.repository,
            name="project 2"
        )

        build2 = self.create_build(
            project=project2,
            source=self.source,
            status=Status.finished,
            result=Result.failed
        )

        job2 = self.create_job(build=build2)

        self.create_plan(project2)

        path = '/api/0/phabricator_diffs/{0}/retry/'.format(self.diff.diff_id)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert len(data) == 2

        data = [Build.query.get(x['id']) for x in data]

        (new_build,) = [x for x in data if x.project_id == build.project_id]

        assert new_build.id != build.id
        assert new_build.collection_id != build.collection_id
        assert new_build.source_id == build.source_id

        jobs = list(Job.query.filter(
            Job.build_id == new_build.id,
        ))

        new_job = jobs[0]
        assert new_job.id != job.id

        (new_build2,) = [x for x in data if x.project_id == build2.project_id]

        assert new_build2.id != build2.id
        assert new_build2.collection_id != build2.collection_id
        assert new_build2.source_id == build2.source_id

        (new_job,) = list(Job.query.filter(
            Job.build_id == new_build2.id,
        ))
        assert new_job.id != job2.id

    @mock.patch('changes.models.repository.Repository.get_vcs')
    def test_when_in_whitelist(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
        po = ProjectOption(
            project=self.project,
            name='build.file-whitelist',
            value='ci/*',
        )
        db.session.add(po)
        db.session.commit()
        build = self.create_build(
            project=self.project,
            source=self.source,
            status=Status.finished,
            result=Result.failed
        )
        job = self.create_job(build=build)

        path = '/api/0/phabricator_diffs/{0}/retry/'.format(self.diff.diff_id)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert len(data) == 1

        new_build = Build.query.get(data[0]['id'])

        assert new_build.id != build.id
        assert new_build.collection_id != build.collection_id
        assert new_build.project_id == build.project_id
        assert new_build.source_id == build.source_id

        (new_job,) = list(Job.query.filter(
            Job.build_id == new_build.id,
        ))
        assert new_job.id != job.id

    @mock.patch('changes.models.repository.Repository.get_vcs')
    def test_when_not_in_whitelist(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
        po = ProjectOption(
            project=self.project,
            name='build.file-whitelist',
            value='nonexisting_directory',
        )
        db.session.add(po)
        db.session.commit()
        build = self.create_build(
            project=self.project,
            source=self.source,
            status=Status.finished,
            result=Result.failed
        )
        self.create_job(build=build)

        path = '/api/0/phabricator_diffs/{0}/retry/'.format(self.diff.diff_id)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert len(data) == 0

    @mock.patch('changes.models.repository.Repository.get_vcs')
    def test_when_in_blacklist(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.read_file.side_effect = None
        fake_vcs.read_file.return_value = yaml.safe_dump({
            'build.file-blacklist': ['ci/*'],
        })
        get_vcs.return_value = fake_vcs
        build = self.create_build(
            project=self.project,
            source=self.source,
            status=Status.finished,
            result=Result.failed
        )
        self.create_job(build=build)

        path = '/api/0/phabricator_diffs/{0}/retry/'.format(self.diff.diff_id)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert len(data) == 0

    @mock.patch('changes.models.repository.Repository.get_vcs')
    def test_when_not_all_in_blacklist(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.read_file.side_effect = None
        fake_vcs.read_file.return_value = yaml.safe_dump({
            'build.file-blacklist': ['ci/not-real'],
        })
        get_vcs.return_value = fake_vcs
        build = self.create_build(
            project=self.project,
            source=self.source,
            status=Status.finished,
            result=Result.failed
        )
        job = self.create_job(build=build)

        path = '/api/0/phabricator_diffs/{0}/retry/'.format(self.diff.diff_id)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert len(data) == 1

        new_build = Build.query.get(data[0]['id'])

        assert new_build.id != build.id
        assert new_build.collection_id != build.collection_id
        assert new_build.project_id == build.project_id
        assert new_build.source_id == build.source_id

        (new_job,) = list(Job.query.filter(
            Job.build_id == new_build.id,
        ))
        assert new_job.id != job.id

    @mock.patch('changes.models.repository.Repository.get_vcs')
    def test_invalid_diff(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.read_file.side_effect = None
        fake_vcs.read_file.return_value = yaml.safe_dump({
            'build.file-blacklist': ['ci/not-real'],
        })
        get_vcs.return_value = fake_vcs
        build = self.create_build(
            project=self.project,
            source=self.source,
            status=Status.finished,
            result=Result.failed
        )
        self.create_job(build=build)

        path = '/api/0/phabricator_diffs/{0}/retry/'.format(self.diff.diff_id)
        with mock.patch('changes.api.diff_build_retry.files_changed_should_trigger_project') as mocked:
            mocked.side_effect = InvalidDiffError
            resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 400

    @mock.patch('changes.models.repository.Repository.get_vcs')
    def test_invalid_config(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.read_file.side_effect = None
        fake_vcs.read_file.return_value = yaml.safe_dump({
            'build.file-blacklist': ['ci/not-real'],
        }) + '}'
        get_vcs.return_value = fake_vcs
        build = self.create_build(
            project=self.project,
            source=self.source,
            status=Status.finished,
            result=Result.failed
        )
        self.create_job(build=build)

        path = '/api/0/phabricator_diffs/{0}/retry/'.format(self.diff.diff_id)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 400
