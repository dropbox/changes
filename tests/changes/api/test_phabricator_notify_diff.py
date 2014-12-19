from __future__ import absolute_import, division, unicode_literals

from cStringIO import StringIO

from changes.config import db
from changes.models import Job, JobPlan, ProjectOption
from changes.testutils import APITestCase, SAMPLE_DIFF
from changes.testutils.build import CreateBuildsMixin


class PhabricatorNotifyDiffTest(APITestCase, CreateBuildsMixin):
    path = '/api/0/phabricator/notify-diff/'

    def post_sample_patch(self):
        return self.client.post(self.path, data={
            'phabricator.callsign': 'FOO',
            'phabricator.diffID': '1324134',
            'phabricator.revisionID': '1234',
            'phabricator.revisionURL': 'https://phabricator.example.com/D1234',
            'patch': (StringIO(SAMPLE_DIFF), 'foo.diff'),
            'sha': 'a' * 40,
            'label': 'Foo Bar',
            'message': 'Hello world!',
            'author': 'David Cramer <dcramer@example.com>',
        })

    def test_valid_params(self):
        repo = self.create_repo()

        project = self.create_project(repository=repo)
        plan = self.create_plan(project)
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )
        db.session.commit()

        resp = self.post_sample_patch()
        assert resp.status_code == 200
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

        assert job.project == project
        assert job.label == plan.label

        assert source.repository_id == project.repository_id
        # TODO(dcramer): re-enable test when find_green_parent_sha is turned
        # assert source.revision_sha == 'b' * 40
        assert source.revision_sha == 'a' * 40
        assert source.data == {
            'phabricator.buildTargetPHID': None,
            'phabricator.diffID': '1324134',
            'phabricator.revisionID': '1234',
            'phabricator.revisionURL': 'https://phabricator.example.com/D1234',
        }

        patch = source.patch
        assert patch.diff == SAMPLE_DIFF
        # we still reference the precise parent revision for patches
        assert patch.parent_revision_sha == 'a' * 40

        jobplans = list(JobPlan.query.filter(
            JobPlan.build_id == build.id,
        ))

        assert len(jobplans) == 1

        assert jobplans[0].job_id == job.id
        assert jobplans[0].plan_id == plan.id
        assert jobplans[0].project_id == project.id

    def test_with_patch_without_diffs_enabled(self):
        repo = self.create_repo()

        project = self.create_project(repository=repo)
        self.create_plan(project)
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )

        po = ProjectOption(
            project=project,
            name='phabricator.diff-trigger',
            value='0',
        )
        db.session.add(po)
        db.session.commit()

        # Default to not creating a build (for tools)
        resp = self.post_sample_patch()
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 0

    def test_when_not_in_whitelist(self):
        repo = self.create_repo()

        project = self.create_project(repository=repo)
        self.create_plan(project)
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )

        po = ProjectOption(
            project=project,
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
        repo = self.create_repo()

        project = self.create_project(repository=repo)
        self.create_plan(project)
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )

        po = ProjectOption(
            project=project,
            name='build.file-whitelist',
            value='ci/*',
        )
        db.session.add(po)
        db.session.commit()

        resp = self.post_sample_patch()
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 1

    def test_collection_id(self):
        repo = self.create_repo_with_projects(count=3)
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )
        db.session.commit()
        resp = self.post_sample_patch()
        builds = self.assert_resp_has_multiple_items(resp, count=3)
        self.assert_collection_id_across_builds(builds)
