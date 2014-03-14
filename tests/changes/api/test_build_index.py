from cStringIO import StringIO

from changes.config import db
from changes.models import Job, JobPlan, ProjectOption
from changes.testutils import APITestCase, SAMPLE_DIFF


class BuildListTest(APITestCase):
    path = '/api/0/builds/'

    def test_simple(self):
        build = self.create_build(self.project)
        build2 = self.create_build(self.project2)

        resp = self.client.get(self.path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == build2.id.hex
        assert data[1]['id'] == build.id.hex


class BuildCreateTest(APITestCase):
    path = '/api/0/builds/'

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
        revision = self.create_revision(sha='a' * 40)
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

    def test_with_full_params(self):
        resp = self.client.post(self.path, data={
            'project': self.project.slug,
            'sha': 'a' * 40,
            'target': 'D1234',
            'label': 'Foo Bar',
            'message': 'Hello world!',
            'author': 'David Cramer <dcramer@example.com>',
            'patch': (StringIO(SAMPLE_DIFF), 'foo.diff'),
            'patch[label]': 'My patch',
        })
        assert resp.status_code == 200, resp.data

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

        assert job.project == self.project
        assert job.label == self.plan.label

        assert source.repository_id == self.project.repository_id
        assert source.revision_sha == 'a' * 40

        patch = source.patch
        assert patch.diff == SAMPLE_DIFF
        assert patch.label == 'My patch'
        assert patch.parent_revision_sha == 'a' * 40

        jobplans = list(JobPlan.query.filter(
            JobPlan.build_id == build.id,
        ))

        assert len(jobplans) == 1

        assert jobplans[0].plan_id == self.plan.id
        assert jobplans[0].project_id == self.project.id

    def test_with_repository(self):
        plan = self.create_plan()
        repo = self.create_repo()

        project1 = self.create_project(repository=repo)
        project2 = self.create_project(repository=repo)
        plan.projects.append(project1)
        plan.projects.append(project2)

        resp = self.client.post(self.path, data={
            'repository': repo.url,
            'sha': 'a' * 40,
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2

    def test_with_patch_without_diffs_enabled(self):
        po = ProjectOption(
            project=self.project,
            name='build.allow-patches',
            value='0',
        )
        db.session.add(po)

        resp = self.client.post(self.path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'patch': (StringIO(SAMPLE_DIFF), 'foo.diff'),
            'patch[label]': 'D1234',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0
