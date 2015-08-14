from __future__ import absolute_import, division, unicode_literals

import yaml

from cStringIO import StringIO
from datetime import datetime
from mock import Mock, patch

from changes.config import db
from changes.models import Job, JobPlan, ProjectOption
from changes.testutils import APITestCase, SAMPLE_DIFF
from changes.testutils.build import CreateBuildsMixin
from changes.vcs.base import CommandError, InvalidDiffError, RevisionResult, Vcs, UnknownRevision


class PhabricatorNotifyDiffTest(APITestCase, CreateBuildsMixin):
    path = '/api/0/phabricator/notify-diff/'

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

        def fake_update():
            # this simulates the effect of calling update() on a repo,
            # mainly that `export` and `log` now works.
            fake_vcs.log.side_effect = log_results
            fake_vcs.export.side_effect = None
            fake_vcs.export.return_value = SAMPLE_DIFF

        fake_vcs.update.side_effect = fake_update

        return fake_vcs

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

    @patch('changes.models.Repository.get_vcs')
    def test_valid_params(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
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

    @patch('changes.models.Repository.get_vcs')
    def test_when_not_in_whitelist(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
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

    @patch('changes.models.Repository.get_vcs')
    def test_when_in_whitelist(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
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

    @patch('changes.models.Repository.get_vcs')
    def test_when_in_blacklist(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.read_file.side_effect = None
        fake_vcs.read_file.return_value = yaml.safe_dump({
            'build.file-blacklist': ['ci/*'],
        })
        get_vcs.return_value = fake_vcs
        repo = self.create_repo()
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )

        project = self.create_project(repository=repo)
        self.create_plan(project)

        resp = self.post_sample_patch()
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 0

    @patch('changes.models.Repository.get_vcs')
    def test_when_not_all_in_blacklist(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.read_file.side_effect = None
        fake_vcs.read_file.return_value = yaml.safe_dump({
            'build.file-blacklist': ['ci/not-real'],
        })
        get_vcs.return_value = fake_vcs
        repo = self.create_repo()
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )

        project = self.create_project(repository=repo)
        self.create_plan(project)

        resp = self.post_sample_patch()
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 1

    @patch('changes.models.Repository.get_vcs')
    def test_invalid_diff(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.read_file.side_effect = None
        fake_vcs.read_file.return_value = yaml.safe_dump({
            'build.file-blacklist': ['ci/*'],
        })
        get_vcs.return_value = fake_vcs
        repo = self.create_repo()
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )

        project = self.create_project(repository=repo)
        self.create_plan(project)

        with patch('changes.api.phabricator_notify_diff.files_changed_should_trigger_project') as mocked:
            mocked.side_effect = InvalidDiffError
            resp = self.post_sample_patch()
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 1

    @patch('changes.models.Repository.get_vcs')
    def test_invalid_config(self, get_vcs):
        fake_vcs = self.get_fake_vcs()
        fake_vcs.read_file.side_effect = None
        fake_vcs.read_file.return_value = yaml.safe_dump({
            'build.file-blacklist': ['ci/*'],
        }) + '}'
        get_vcs.return_value = fake_vcs
        repo = self.create_repo()
        self.create_option(
            item_id=repo.id,
            name='phabricator.callsign',
            value='FOO',
        )

        project = self.create_project(repository=repo)
        self.create_plan(project)

        resp = self.post_sample_patch()
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 1

    @patch('changes.models.Repository.get_vcs')
    def test_collection_id(self, get_vcs):
        get_vcs.return_value = self.get_fake_vcs()
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
