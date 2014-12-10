from cStringIO import StringIO
from mock import patch, Mock

from changes.api.build_index import find_green_parent_sha
from changes.config import db
from changes.constants import Status, Result
from changes.models import Job, JobPlan, ProjectOption
from changes.testutils import APITestCase, TestCase, SAMPLE_DIFF
from changes.vcs.base import Vcs, RevisionResult


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


class BuildCreateTest(APITestCase):
    path = '/api/0/builds/'

    def setUp(self):
        self.project = self.create_project()
        self.plan = self.create_plan(self.project)
        db.session.commit()
        super(BuildCreateTest, self).setUp()

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

    def test_defaults_to_revision(self):
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40,
        )
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

        assert build.message == revision.message
        assert build.author == revision.author
        assert build.label == revision.subject

        assert job.project == self.project

        assert source.repository_id == self.project.repository_id
        assert source.revision_sha == 'a' * 40

    @patch('changes.models.Repository.get_vcs')
    def test_error_on_invalid_revision(self, get_vcs):
        def log_results(parent=None, branch=None, offset=0, limit=1):
            assert not branch
            return iter([
                RevisionResult(
                    id='a' * 40,
                    message='hello world',
                    author='Foo <foo@example.com>',
                )])

        # Fake having a VCS and stub the returned commit log
        fake_vcs = Mock(spec=Vcs)
        fake_vcs.log.side_effect = log_results
        get_vcs.return_value = fake_vcs

        # Try a commit SHA that doesn't match the stub above
        resp = self.client.post(self.path, data={
            'sha': 'z' * 40,
            'project': self.project.slug,
        })
        assert resp.status_code == 400
        data = self.unserialize(resp)
        assert 'error' in data
        assert 'problems' in data
        assert 'sha' in data['problems']

    def post_sample_patch(self):
        return self.client.post(self.path, data={
            'project': self.project.slug,
            'sha': 'a' * 40,
            'target': 'D1234',
            'label': 'Foo Bar',
            'message': 'Hello world!',
            'author': 'David Cramer <dcramer@example.com>',
            'patch': (StringIO(SAMPLE_DIFF), 'foo.diff'),
            'patch[data]': '{"foo": "bar"}',
        })

    def test_when_not_in_whitelist(self):
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

    def test_when_in_whitelist(self):
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

    def test_with_repository(self):
        repo = self.create_repo()

        project1 = self.create_project(repository=repo)
        project2 = self.create_project(repository=repo)
        self.create_plan(project1)
        self.create_plan(project2)
        db.session.commit()

        resp = self.client.post(self.path, data={
            'repository': repo.url,
            'sha': 'a' * 40,
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2

    def test_with_repository_callsign(self):
        repo = self.create_repo()

        project1 = self.create_project(repository=repo)
        project2 = self.create_project(repository=repo)
        self.create_plan(project1)
        self.create_plan(project2)
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
