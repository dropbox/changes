from cStringIO import StringIO

from changes.config import db
from changes.models import Job, JobPlan, Patch, ProjectOption
from changes.testutils import APITestCase, SAMPLE_DIFF


class BuildListTest(APITestCase):
    def test_simple(self):
        change = self.create_change(self.project)
        build = self.create_build(self.project, change=change)
        self.create_build(self.project2)

        path = '/api/0/changes/{0}/builds/'.format(change.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['builds']) == 1
        assert data['builds'][0]['id'] == build.id.hex


class BuildCreateTest(APITestCase):
    def assertBuildMatchesFamily(self, build, family):
        assert family.id == build.family_id
        assert family.repository_id == build.repository_id
        assert family.project_id == build.project_id
        assert family.author_id == build.author_id
        assert family.label == build.label
        assert family.target == build.target
        assert family.message == build.message
        assert family.revision_sha == build.revision_sha
        assert family.status == build.status

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

        build = Job.query.get(data['builds'][0]['id'])

        assert build.project == self.project
        assert build.revision_sha is None
        assert build.author.name == 'David Cramer'
        assert build.author.email == 'dcramer@example.com'

        family = build.family

        self.assertBuildMatchesFamily(build, family)

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
        build = Job.query.get(data['builds'][0]['id'])
        assert build.project == self.project
        assert build.revision_sha == 'a' * 40
        assert build.author.name == 'David Cramer'
        assert build.author.email == 'dcramer@example.com'

        source = build.source
        assert source.repository_id == build.repository_id
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

        build = Job.query.get(data['builds'][0]['id'])
        assert build.change == change
        assert build.project == self.project
        assert build.revision_sha == 'a' * 40
        assert build.author.name == 'David Cramer'
        assert build.author.email == 'dcramer@example.com'
        assert build.message == 'Hello world!'
        assert build.label == 'Foo Bar'
        assert build.target == 'D1234'
        assert build.patch_id is not None

        patch = Patch.query.get(build.patch_id)
        assert patch.diff == SAMPLE_DIFF
        assert patch.label == 'My patch'
        assert patch.parent_revision_sha == 'a' * 40

        source = build.source
        assert source.repository_id == build.repository_id
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

        build = Job.query.get(data['builds'][0]['id'])
        assert build.patch_id is not None
        patch = Patch.query.get(build.patch_id)
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

        buildplans = list(JobPlan.query.filter(
            JobPlan.job_id == data['builds'][0]['id'],
        ))

        assert len(buildplans) == 1

        assert buildplans[0].plan_id == plan.id
        assert buildplans[0].project_id == self.project.id

        job = buildplans[0].job
        family = buildplans[0].family

        self.assertBuildMatchesFamily(job, family)
