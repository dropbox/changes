import json

from cStringIO import StringIO
from datetime import datetime
from mock import MagicMock

from mock import patch, Mock
from changes.api.build_index import find_green_parent_sha
from changes.config import db
from changes.constants import Status, Result
from changes.models import Job, JobPlan, Patch, ProjectOption
from changes.testutils import APITestCase, TestCase, SAMPLE_DIFF
from changes.vcs.base import RevisionResult, Vcs, UnknownRevision
from changes.testutils.build import CreateBuildsMixin


class FindGreenParentShaTest(TestCase):
    # TODO(dcramer): we should add checks for builds from other projects
    # as they shouldn't be included with the green build query
    def test_current_green(self):
        project = self.create_project()
        current_source = self.create_source(
            project=project,
            revision_sha='a' * 40,
        )
        newer_source = self.create_source(
            project=project,
            revision_sha='b' * 40,
        )
        current_build = self.create_build(  # NOQA
            project=project,
            source=current_source,
            status=Status.finished,
            result=Result.passed,
        )
        newer_build = self.create_build(  # NOQA
            project=project,
            source=newer_source,
            status=Status.finished,
            result=Result.passed,
        )

        result = find_green_parent_sha(project, current_source.revision_sha)
        assert result == current_source.revision_sha

    def test_newer_green(self):
        project = self.create_project()
        older_source = self.create_source(
            project=project,
            revision_sha='c' * 40,
        )
        current_source = self.create_source(
            project=project,
            revision_sha='a' * 40,
        )
        newer_source = self.create_source(
            project=project,
            revision_sha='b' * 40,
        )
        older_build = self.create_build(  # NOQA
            project=project,
            source=older_source,
            status=Status.finished,
            result=Result.passed,
        )
        current_build = self.create_build(  # NOQA
            project=project,
            source=current_source,
            status=Status.finished,
            result=Result.failed,
        )
        newer_build = self.create_build(  # NOQA
            project=project,
            source=newer_source,
            status=Status.finished,
            result=Result.passed,
        )
        result = find_green_parent_sha(project, current_source.revision_sha)
        assert result == newer_source.revision_sha

    def test_newer_green_missing_revision(self):
        project = self.create_project()
        current_source = self.create_source(
            project=project,
            revision_sha='a' * 40,
        )
        newer_source = self.create_source(
            project=project,
            revision_sha=None,
        )
        newer_build = self.create_build(  # NOQA
            project=project,
            source=newer_source,
            status=Status.finished,
            result=Result.passed,
        )
        result = find_green_parent_sha(project, current_source.revision_sha)
        assert result == current_source.revision_sha

    def test_newer_green_is_patch(self):
        project = self.create_project()
        current_source = self.create_source(
            project=project,
            revision_sha='a' * 40,
        )
        newer_source = self.create_source(
            project=project,
            revision_sha='b' * 40,
            patch=self.create_patch(repository=project.repository),
        )
        newer_build = self.create_build(  # NOQA
            project=project,
            source=newer_source,
            status=Status.finished,
            result=Result.passed,
        )
        result = find_green_parent_sha(project, current_source.revision_sha)
        assert result == current_source.revision_sha

    def test_without_newer_green(self):
        project = self.create_project()
        older_source = self.create_source(
            project=project,
            revision_sha='c' * 40,
        )
        current_source = self.create_source(
            project=project,
            revision_sha='a' * 40,
        )
        newer_source = self.create_source(
            project=project,
            revision_sha='b' * 40,
        )
        older_build = self.create_build(  # NOQA
            project=project,
            source=older_source,
            status=Status.finished,
            result=Result.passed,
        )
        current_build = self.create_build(  # NOQA
            project=project,
            source=current_source,
            status=Status.finished,
            result=Result.failed,
        )
        newer_build = self.create_build(  # NOQA
            project=project,
            source=newer_source,
            status=Status.finished,
            result=Result.failed,
        )
        result = find_green_parent_sha(project, current_source.revision_sha)
        assert result == current_source.revision_sha

    def test_without_any_builds(self):
        project = self.create_project()
        result = find_green_parent_sha(project, 'a' * 40)
        assert result == 'a' * 40


class BuildListTest(APITestCase):
    path = '/api/0/builds/'

    def test_simple(self):
        project = self.create_project()
        project2 = self.create_project()
        build = self.create_build(project)
        build2 = self.create_build(project2)

        resp = self.client.get(self.path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == build2.id.hex
        assert data[1]['id'] == build.id.hex


class BuildCreateTest(APITestCase, CreateBuildsMixin):
    path = '/api/0/builds/'

    def setUp(self):
        self.project = self.create_project()
        self.plan = self.create_plan(self.project)
        db.session.commit()
        super(BuildCreateTest, self).setUp()

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
        fake_vcs.exists.return_value = True
        fake_vcs.log.side_effect = UnknownRevision(cmd="test command", retcode=128)
        fake_vcs.export.side_effect = UnknownRevision(cmd="test command", retcode=128)

        def fake_update():
            # this simulates the effect of calling update() on a repo,
            # mainly that `export` and `log` now works.
            fake_vcs.log.side_effect = log_results
            fake_vcs.export.side_effect = None
            fake_vcs.export.return_value = SAMPLE_DIFF

        fake_vcs.update.side_effect = fake_update

        return fake_vcs

    def test_minimal(self):
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id']

        job = Job.query.filter(
            Job.build_id == data[0]['id']
        ).first()
        build = job.build
        source = build.source

        assert job.project == self.project

        assert source.repository_id == self.project.repository_id
        assert source.revision_sha == 'a' * 40

    @patch('changes.models.Repository.get_vcs')
    def test_defaults_to_revision(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.update.side_effect = None
        get_vcs.return_value = fake_vcs
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40,
        )
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'apply_file_whitelist': '',  # file whitelist requires git, which we disabled
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id']

        job = Job.query.filter(
            Job.build_id == data[0]['id']
        ).first()
        build = job.build
        source = build.source

        assert build.message == revision.message
        assert build.author == revision.author
        assert build.label == revision.subject

        assert job.project == self.project

        assert source.repository_id == self.project.repository_id
        assert source.revision_sha == 'a' * 40

    @patch('changes.models.Repository.get_vcs')
    def test_defaults_to_revision_not_found(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.update.side_effect = None
        get_vcs.return_value = fake_vcs
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40,
        )
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'apply_file_whitelist': '1',  # This requires that git be updated
        })
        assert resp.status_code == 400
        data = self.unserialize(resp)
        assert 'error' in data
        assert 'problems' in data
        assert 'sha' in data['problems']
        assert 'repository' in data['problems']

    @patch('changes.models.Repository.get_vcs')
    def test_error_on_invalid_revision(self, get_vcs):
        def log_results(parent=None, branch=None, offset=0, limit=1):
            assert not branch
            ret = MagicMock()
            ret.next.side_effect = UnknownRevision(cmd="test command", retcode=128)
            return ret

        # Fake having a VCS and stub the returned commit log
        get_vcs.return_value = self.get_fake_vcs(log_results=log_results)

        # try any commit sha, since we mocked out log_results
        resp = self.client.post(self.path, data={
            'sha': 'z' * 40,
            'project': self.project.slug,
        })
        assert resp.status_code == 400
        data = self.unserialize(resp)
        assert 'error' in data
        assert 'problems' in data
        assert 'sha' in data['problems']

    def post_sample_patch(self, data=None):
        if data is None:
            data = {}
        data['project'] = self.project.slug
        data['sha'] = 'a' * 40
        data['target'] = 'D1234'
        data['label'] = 'Foo Bar'
        data['message'] = 'Hello world!'
        data['author'] = 'David Cramer <dcramer@example.com>'
        data['patch'] = (StringIO(SAMPLE_DIFF), 'foo.diff')
        data['patch[data]'] = '{"foo": "bar"}'
        return self.client.post(self.path, data=data)

    def test_when_not_in_whitelist_diff_build(self):
        po = ProjectOption(
            project=self.project,
            name='build.file-whitelist',
            value='nonexisting_directory',
        )
        db.session.add(po)
        db.session.commit()

        resp = self.post_sample_patch({
            'apply_file_whitelist': '1',
        })
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 0

    def test_when_in_whitelist_diff_build(self):
        po = ProjectOption(
            project=self.project,
            name='build.file-whitelist',
            value='ci/*',
        )
        db.session.add(po)
        db.session.commit()

        resp = self.post_sample_patch({
            'apply_file_whitelist': '1',
        })
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 1

    def test_when_in_whitelist_diff_build_default_true(self):
        po = ProjectOption(
            project=self.project,
            name='build.file-whitelist',
            value='ci/*',
        )
        db.session.add(po)
        db.session.commit()

        resp = self.post_sample_patch()
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 1

    def test_when_in_whitelist_diff_build_default_true_negative(self):
        po = ProjectOption(
            project=self.project,
            name='build.file-whitelist',
            value='nonexisting_directory',
        )
        db.session.add(po)
        db.session.commit()

        resp = self.post_sample_patch()
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 0

    @patch('changes.models.Repository.get_vcs')
    def test_when_not_in_whitelist_commit_build(self, get_vcs):
        po = ProjectOption(
            project=self.project,
            name='build.file-whitelist',
            value='nonexisting_directory',
        )
        db.session.add(po)
        db.session.commit()
        get_vcs.return_value = self.get_fake_vcs()
        self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        resp = self.client.post(self.path, data={
            'apply_file_whitelist': '1',
            'sha': 'a' * 40,
            'repository': self.project.repository.url
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0

    @patch('changes.models.Repository.get_vcs')
    def test_when_in_whitelist_commit_build(self, get_vcs):
        po = ProjectOption(
            project=self.project,
            name='build.file-whitelist',
            value='ci/*',
        )
        db.session.add(po)
        db.session.commit()
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        resp = self.client.post(self.path, data={
            'apply_file_whitelist': '1',
            'sha': 'a' * 40,
            'repository': self.project.repository.url
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id']

        job = Job.query.filter(
            Job.build_id == data[0]['id']
        ).first()
        build = job.build
        source = build.source

        assert job.project == self.project
        assert source.revision_sha == revision.sha

    @patch('changes.models.Repository.get_vcs')
    def test_when_in_whitelist_commit_build_default_false(self, get_vcs):
        po = ProjectOption(
            project=self.project,
            name='build.file-whitelist',
            value='nonexisting_directory',
        )
        db.session.add(po)
        db.session.commit()
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'repository': self.project.repository.url
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id']

        job = Job.query.filter(
            Job.build_id == data[0]['id']
        ).first()
        build = job.build
        source = build.source

        assert job.project == self.project
        assert source.revision_sha == revision.sha

    @patch('changes.models.Repository.get_vcs')
    def test_when_in_whitelist_commit_build_false(self, get_vcs):
        po = ProjectOption(
            project=self.project,
            name='build.file-whitelist',
            value='nonexisting_directory',
        )
        db.session.add(po)
        db.session.commit()
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'repository': self.project.repository.url,
            'apply_file_whitelist': '',
            'ensure_only': '1',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id']

        job = Job.query.filter(
            Job.build_id == data[0]['id']
        ).first()
        build = job.build
        source = build.source

        assert job.project == self.project
        assert source.revision_sha == revision.sha

    @patch('changes.models.Repository.get_vcs')
    def test_ensure_existing_build_complete(self, get_vcs):
        """Tests when all builds have already been created"""
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        source = self.create_source(self.project, revision=revision)
        build = self.create_build(self.project, source=source)
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'apply_file_whitelist': '1',
            'ensure_only': '1',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build.id.hex

    @patch('changes.models.Repository.get_vcs')
    def test_ensure_existing_build_incomplete(self, get_vcs):
        """Tests when only a subset of the builds have been created"""
        project2 = self.create_project(repository=self.project.repository)
        self.create_plan(project2)
        db.session.commit()
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        source = self.create_source(self.project, revision=revision)
        build = self.create_build(self.project, source=source)
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'repository': self.project.repository.url,
            'apply_file_whitelist': '1',
            'ensure_only': '1',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert len([x for x in data if x['id'] == build.id.hex]) == 1
        assert len(
            [x for x in data if x['project']['slug'] == self.project.slug]) == 1
        assert len(
            [x for x in data if x['project']['slug'] == project2.slug]) == 1

    @patch('changes.models.Repository.get_vcs')
    def test_ensure_multiple_existing_build(self, get_vcs):
        """Tests when only a subset of the builds have been created"""
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        source = self.create_source(self.project, revision=revision)

        # this is older and won't be returned
        self.create_build(self.project, source=source)
        build = self.create_build(self.project, source=source)
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'repository': self.project.repository.url,
            'apply_file_whitelist': '1',
            'ensure_only': '1',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build.id.hex
        assert data[0]['project']['slug'] == self.project.slug

    @patch('changes.models.Repository.get_vcs')
    def test_ensure_existing_build_wrong_revision(self, get_vcs):
        """Tests when other builds in the system exist"""
        get_vcs.return_value = self.get_fake_vcs()
        wrong_revision = self.create_revision(
            repository=self.project.repository,
            sha='b' * 40
        )
        source = self.create_source(self.project, revision=wrong_revision)

        # this is older and won't be returned
        self.create_build(self.project, source=source)
        build = self.create_build(self.project, source=source)
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'repository': self.project.repository.url,
            'apply_file_whitelist': '1',
            'ensure_only': '1',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] != build.id.hex

    @patch('changes.models.Repository.get_vcs')
    def test_ensure_existing_build_false(self, get_vcs):
        """Tests when existing builds have been created,
        but we don't want to run in ensure-only mode explicitly
        """
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        source = self.create_source(self.project, revision=revision)
        build = self.create_build(self.project, source=source)
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'apply_file_whitelist': '1',
            'ensure_only': '',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] != build.id.hex

    @patch('changes.models.Repository.get_vcs')
    def test_ensure_existing_build_default_false(self, get_vcs):
        """Tests when existing builds have been created,
        but we don't want to run in ensure-only mode by default
        """
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        source = self.create_source(self.project, revision=revision)
        build = self.create_build(self.project, source=source)
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'apply_file_whitelist': '1',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] != build.id.hex

    @patch('changes.models.Repository.get_vcs')
    def test_ensure_match_patch_want_commit(self, get_vcs):
        """This makes sure that the ensure API handles diff builds correctly.
        This is the case where we want to ensure a commit build.
        """
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        patch = Patch(
            repository=self.project.repository,
            parent_revision_sha=revision.sha,
            diff=SAMPLE_DIFF,
        )
        source = self.create_source(self.project, revision=revision)
        bad_source = self.create_source(self.project, revision=revision, patch=patch)
        build = self.create_build(self.project, source=source)

        # if diff builds weren't handled properly, this build would be older
        # and would be returned
        self.create_build(self.project, source=bad_source)
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'apply_file_whitelist': '1',
            'ensure_only': '1',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build.id.hex

    def test_ensure_match_patch_want_diff_error(self):
        """This tests that ensure-only mode does not work with diff builds.
        """
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'apply_file_whitelist': '1',
            'ensure_only': '1',
            'patch': (StringIO(SAMPLE_DIFF), 'foo.diff'),
        })
        assert resp.status_code == 400
        data = self.unserialize(resp)
        assert 'patch' in data['problems']
        assert 'ensure_only' in data['problems']

    @patch('changes.models.Repository.get_vcs')
    def test_existing_build_wrong_revision(self, get_vcs):
        """Tests when other builds in the system exist"""
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        wrong_revision = self.create_revision(
            repository=self.project.repository,
            sha='b' * 40
        )
        source = self.create_source(self.project, revision=wrong_revision)

        # this is older and won't be returned
        self.create_build(self.project, source=source)
        build = self.create_build(self.project, source=source)
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'repository': self.project.repository.url
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] != build.id.hex

    @patch('changes.models.Repository.get_vcs')
    def test_with_project_whitelist(self, get_vcs):
        project2 = self.create_project(repository=self.project.repository)
        self.create_plan(project2)
        db.session.commit()
        get_vcs.return_value = self.get_fake_vcs()
        self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'repository': self.project.repository.url,
            'project_whitelist': json.dumps([project2.slug]),
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        job = Job.query.filter(
            Job.build_id == data[0]['id']
        ).first()
        build = job.build

        assert job.project == project2

    @patch('changes.models.Repository.get_vcs')
    def test_with_project_whitelist_empty(self, get_vcs):
        project2 = self.create_project(repository=self.project.repository)
        self.create_plan(project2)
        db.session.commit()
        get_vcs.return_value = self.get_fake_vcs()
        self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'repository': self.project.repository.url,
            'project_whitelist': json.dumps([]),
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0

    @patch('changes.api.build_index.find_green_parent_sha')
    def test_with_full_params(self, mock_find_green_parent_sha):
        mock_find_green_parent_sha.return_value = 'b' * 40

        resp = self.post_sample_patch()
        assert resp.status_code == 200, resp.data

        # TODO(dcramer): re-enable test when find_green_parent_sha is turned
        # back on
        # mock_find_green_parent_sha.assert_called_once_with(
        #     project=self.project,
        #     sha='a' * 40,
        # )

        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id']

        job = Job.query.filter(
            Job.build_id == data[0]['id']
        ).first()
        build = job.build
        source = build.source

        assert build.author.name == 'David Cramer'
        assert build.author.email == 'dcramer@example.com'
        assert build.message == 'Hello world!'
        assert build.label == 'Foo Bar'
        assert build.target == 'D1234'

        assert job.project == self.project
        assert job.label == self.plan.label

        assert source.repository_id == self.project.repository_id
        # TODO(dcramer): re-enable test when find_green_parent_sha is turned
        # assert source.revision_sha == 'b' * 40
        assert source.revision_sha == 'a' * 40
        assert source.data == {'foo': 'bar'}

        patch = source.patch
        assert patch.diff == SAMPLE_DIFF
        # we still reference the precise parent revision for patches
        assert patch.parent_revision_sha == 'a' * 40

        jobplans = list(JobPlan.query.filter(
            JobPlan.build_id == build.id,
        ))

        assert len(jobplans) == 1

        assert jobplans[0].job_id == job.id
        assert jobplans[0].plan_id == self.plan.id
        assert jobplans[0].project_id == self.project.id

    def _post_for_repo(self, repo):
        return self.client.post(self.path, data={
            'repository': repo.url,
            'sha': 'a' * 40,
        })

    def test_with_repository(self):
        repo = self.create_repo_with_projects(count=2)
        resp = self._post_for_repo(repo)
        self.assert_resp_has_multiple_items(resp, count=2)

    def test_collection_id(self):
        repo = self.create_repo_with_projects(count=3)
        resp = self._post_for_repo(repo)
        builds = self.assert_resp_has_multiple_items(resp, count=3)
        self.assert_collection_id_across_builds(builds)

    def test_with_repository_callsign(self):
        repo = self.create_repo_with_projects(count=2)
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )
        db.session.commit()

        resp = self.client.post(self.path, data={
            'repository[phabricator.callsign]': 'FOO',
            'sha': 'a' * 40,
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
