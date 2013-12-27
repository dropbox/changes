from cStringIO import StringIO

from changes.config import db
from changes.models import Job, JobPlan, Patch, ProjectOption
from changes.testutils import APITestCase, SAMPLE_DIFF


class BuildListTest(APITestCase):
    def test_simple(self):
        change = self.create_change(self.project)
        build = self.create_build(self.project)
        job = self.create_job(build, change=change)
        build2 = self.create_build(self.project2)
        self.create_job(build2)

        path = '/api/0/changes/{0}/builds/'.format(change.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['builds']) == 1
        assert data['builds'][0]['id'] == job.id.hex


class BuildCreateTest(APITestCase):
    def assertJobMatchesBuild(self, job, build):
        assert build.id == job.build_id
        assert build.repository_id == job.repository_id
        assert build.project_id == job.project_id
        assert build.author_id == job.author_id
        assert build.target == job.target
        assert build.message == job.message
        assert build.revision_sha == job.revision_sha
        assert build.status == job.status

    def test_simple(self):
        path = '/api/0/builds/'
        resp = self.client.post(path, data={
            'author': 'David Cramer <dcramer@example.com>',
            'project': self.project.slug,
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['builds']) == 1
        assert data['builds'][0]['id']

        job = Job.query.filter(
            Job.build_id == data['builds'][0]['id']
        ).first()

        assert job.number == 1
        assert job.project == self.project
        assert job.revision_sha is None
        assert job.author.name == 'David Cramer'
        assert job.author.email == 'dcramer@example.com'

        build = job.build

        assert build.number == 1

        self.assertJobMatchesBuild(job, build)

    def test_with_sha(self):
        path = '/api/0/builds/'
        resp = self.client.post(path, data={
            'sha': 'a' * 40,
            'author': 'David Cramer <dcramer@example.com>',
            'project': self.project.slug,
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['builds']) == 1
        assert data['builds'][0]['id']

        job = Job.query.filter(
            Job.build_id == data['builds'][0]['id']
        ).first()

        assert job.project == self.project
        assert job.revision_sha == 'a' * 40
        assert job.author.name == 'David Cramer'
        assert job.author.email == 'dcramer@example.com'

        source = job.source
        assert source.repository_id == job.repository_id
        assert source.revision_sha == 'a' * 40

    def test_with_full_params(self):
        change = self.create_change(self.project)
        path = '/api/0/builds/'
        resp = self.client.post(path, data={
            'change': change.id.hex,
            'sha': 'a' * 40,
            'target': 'D1234',
            'label': 'Foo Bar',
            'message': 'Hello world!',
            'author': 'David Cramer <dcramer@example.com>',
            'patch': (StringIO(SAMPLE_DIFF), 'foo.diff'),
            'patch[label]': 'My patch',
        })
        assert resp.status_code == 200

        data = self.unserialize(resp)
        assert len(data['builds']) == 1
        assert data['builds'][0]['id']

        job = Job.query.filter(
            Job.build_id == data['builds'][0]['id']
        ).first()

        assert job.change == change
        assert job.project == self.project
        assert job.revision_sha == 'a' * 40
        assert job.author.name == 'David Cramer'
        assert job.author.email == 'dcramer@example.com'
        assert job.message == 'Hello world!'
        assert job.label == 'Foo Bar'
        assert job.target == 'D1234'
        assert job.patch_id is not None

        patch = Patch.query.get(job.patch_id)
        assert patch.diff == SAMPLE_DIFF
        assert patch.label == 'My patch'
        assert patch.parent_revision_sha == 'a' * 40

        source = job.source
        assert source.repository_id == job.repository_id
        assert source.revision_sha == 'a' * 40
        assert source.patch_id == patch.id

    def test_with_patch_without_change(self):
        path = '/api/0/builds/'
        resp = self.client.post(path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'author': 'David Cramer <dcramer@example.com>',
            'patch': (StringIO(SAMPLE_DIFF), 'foo.diff'),
            'patch[label]': 'D1234',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['builds']) == 1
        assert data['builds'][0]['id']

        job = Job.query.filter(
            Job.build_id == data['builds'][0]['id']
        ).first()

        assert job.patch_id is not None
        patch = Patch.query.get(job.patch_id)
        assert patch.diff == SAMPLE_DIFF
        assert patch.label == 'D1234'
        assert patch.parent_revision_sha == 'a' * 40

    def test_with_repository(self):
        path = '/api/0/builds/'

        repo = self.create_repo()

        self.create_project(repository=repo)
        self.create_project(repository=repo)

        resp = self.client.post(path, data={
            'author': 'David Cramer <dcramer@example.com>',
            'repository': repo.url,
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['builds']) == 2

    def test_with_patch_without_diffs_enabled(self):
        po = ProjectOption(
            project=self.project,
            name='build.allow-patches',
            value='0',
        )
        db.session.add(po)

        path = '/api/0/builds/'
        resp = self.client.post(path, data={
            'sha': 'a' * 40,
            'project': self.project.slug,
            'author': 'David Cramer <dcramer@example.com>',
            'patch': (StringIO(SAMPLE_DIFF), 'foo.diff'),
            'patch[label]': 'D1234',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['builds']) == 0

    def test_with_plan(self):
        plan = self.create_plan()
        plan.projects.append(self.project)
        self.create_step(plan)

        path = '/api/0/builds/'
        resp = self.client.post(path, data={
            'project': self.project.slug,
            'author': 'David Cramer <dcramer@example.com>',
        })

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert len(data['builds']) == 1

        jobplans = list(JobPlan.query.filter(
            JobPlan.build_id == data['builds'][0]['id'],
        ))

        assert len(jobplans) == 1

        assert jobplans[0].plan_id == plan.id
        assert jobplans[0].project_id == self.project.id

        job = jobplans[0].job
        build = jobplans[0].build

        self.assertJobMatchesBuild(job, build)
