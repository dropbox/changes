from datetime import datetime
from mock import patch, Mock

from changes.config import db
from changes.models import Job, ProjectOption
from changes.testutils import APITestCase
from changes.testutils.build import CreateBuildsMixin
from changes.testutils.fixtures import SAMPLE_DIFF
from changes.vcs.base import Vcs, RevisionResult


def log_results(parent=None, branch=None, offset=0, limit=1):
    assert not branch
    return iter([
        RevisionResult(
            id='a' * 40,
            message='hello world',
            author='Foo <foo@example.com>',
            author_date=datetime.utcnow(),
        )])


class BuildEnsureTest(APITestCase, CreateBuildsMixin):
    path = '/api/0/builds/revision/ensure/'

    def setUp(self):
        self.project = self.create_project()
        self.plan = self.create_plan(self.project)
        db.session.commit()
        super(BuildEnsureTest, self).setUp()

    def get_fake_vcs(self):
        # Fake having a VCS and stub the returned commit log
        fake_vcs = Mock(spec=Vcs)
        fake_vcs.log.side_effect = log_results
        fake_vcs.exists.return_value = True
        fake_vcs.export.return_value = SAMPLE_DIFF
        return fake_vcs

    @patch('changes.models.Repository.get_vcs')
    def test_simple(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
        revision = self.create_revision(
            repository=self.project.repository,
            sha='a' * 40
        )
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug
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
        assert source.revision_sha == revision.sha

    @patch('changes.models.Repository.get_vcs')
    def test_simple_no_revision(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug
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
    def test_when_not_in_whitelist(self, get_vcs):
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
            'sha': 'a' * 40,
            'project': self.project.slug
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0

    @patch('changes.models.Repository.get_vcs')
    def test_when_in_whitelist(self, get_vcs):
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
            'sha': 'a' * 40,
            'project': self.project.slug
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
    def test_existing_build_complete(self, get_vcs):
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
            'project': self.project.slug
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build.id.hex

    @patch('changes.models.Repository.get_vcs')
    def test_existing_build_incomplete(self, get_vcs):
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
            'repository': self.project.repository.url
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
    def test_multiple_existing_build(self, get_vcs):
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
            'repository': self.project.repository.url
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build.id.hex
        assert data[0]['project']['slug'] == self.project.slug

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
